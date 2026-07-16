package com.testmind.controller;

import com.testmind.dto.*;
import com.testmind.model.PerformanceTestResult;
import com.testmind.repository.PerformanceTestResultRepository;
import com.testmind.service.GithubActionsClient;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/performance")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Performance", description = "Trigger and track Locust load tests via the Performance Gate GitHub Actions workflow")
public class PerformanceController {

    private static final List<String> SUPPORTED_SYSTEMS = List.of("QAIP", "ARIA");

    private final GithubActionsClient githubActionsClient;
    private final PerformanceTestResultRepository resultRepository;

    @Value("${performance.callback.secret:}")
    private String callbackSecret;

    @PostMapping("/run")
    @Operation(summary = "Dispatch the Performance Gate workflow for a given system")
    public ResponseEntity<PerformanceRunResponse> run(@Valid @RequestBody PerformanceRunRequest request) {
        String system = request.getSystem().toUpperCase();
        if (!SUPPORTED_SYSTEMS.contains(system)) {
            return ResponseEntity.badRequest().body(PerformanceRunResponse.builder()
                    .dispatched(false)
                    .message("Unsupported system: " + request.getSystem() + " (supported: " + SUPPORTED_SYSTEMS + ")")
                    .build());
        }
        if (!githubActionsClient.isConfigured()) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(PerformanceRunResponse.builder()
                    .dispatched(false)
                    .message("GITHUB_ACTIONS_TOKEN is not configured on the backend")
                    .build());
        }

        OffsetDateTime dispatchedAt = OffsetDateTime.now();
        try {
            githubActionsClient.dispatchWorkflow(system, request.getHost(), request.getUsers(), request.getRunTime());
        } catch (Exception e) {
            log.error("Failed to dispatch performance workflow: {}", e.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(PerformanceRunResponse.builder()
                    .dispatched(false)
                    .message("Failed to dispatch workflow: " + e.getMessage())
                    .build());
        }

        return ResponseEntity.ok(PerformanceRunResponse.builder()
                .dispatched(true)
                .dispatchedAt(dispatchedAt.toString())
                .message("Workflow dispatched — poll /api/performance/run/status with this dispatchedAt")
                .build());
    }

    @GetMapping("/run/status")
    @Operation(summary = "Find the run matching a previous dispatch and report its status")
    public ResponseEntity<PerformanceRunStatusResponse> runStatus(@RequestParam String dispatchedAt) {
        OffsetDateTime parsed;
        try {
            parsed = OffsetDateTime.parse(dispatchedAt);
        } catch (DateTimeParseException e) {
            return ResponseEntity.badRequest().build();
        }

        Optional<Map<String, Object>> run = githubActionsClient.findRunDispatchedAfter(parsed);
        if (run.isEmpty()) {
            return ResponseEntity.ok(PerformanceRunStatusResponse.builder().status("not_found").build());
        }

        Map<String, Object> r = run.get();
        return ResponseEntity.ok(PerformanceRunStatusResponse.builder()
                .status((String) r.get("status"))
                .conclusion((String) r.get("conclusion"))
                .runUrl((String) r.get("html_url"))
                .build());
    }

    @PostMapping("/results")
    @Operation(summary = "Receive a batch of performance metrics pushed by the workflow's final step")
    public ResponseEntity<Void> receiveResults(
            @RequestHeader(value = "X-Performance-Secret", required = false) String secret,
            @Valid @RequestBody List<PerformanceResultRequest> results) {

        if (callbackSecret == null || callbackSecret.isBlank() || !callbackSecret.equals(secret)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }

        List<PerformanceTestResult> entities = results.stream().map(r -> PerformanceTestResult.builder()
                .system(r.getSystem().toUpperCase())
                .buildSha(r.getBuildSha())
                .endpoint(r.getEndpoint())
                .p50Ms(r.getP50Ms())
                .p95Ms(r.getP95Ms())
                .p99Ms(r.getP99Ms())
                .requestsPerSec(r.getRequestsPerSec())
                .errorRatePct(r.getErrorRatePct())
                .totalRequests(r.getTotalRequests())
                .totalFailures(r.getTotalFailures())
                .passedGate(r.getPassedGate())
                .testedAt(OffsetDateTime.now())
                .build()).toList();

        resultRepository.saveAll(entities);
        log.info("Stored {} performance results", entities.size());
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }

    @GetMapping("/results")
    @Operation(summary = "List recent performance results for a system")
    public ResponseEntity<List<PerformanceResultResponse>> listResults(
            @RequestParam(defaultValue = "QAIP") String system) {

        List<PerformanceResultResponse> response = resultRepository
                .findBySystemOrderByTestedAtDesc(system.toUpperCase())
                .stream()
                .map(r -> PerformanceResultResponse.builder()
                        .id(r.getId())
                        .system(r.getSystem())
                        .buildSha(r.getBuildSha())
                        .endpoint(r.getEndpoint())
                        .p50Ms(r.getP50Ms())
                        .p95Ms(r.getP95Ms())
                        .p99Ms(r.getP99Ms())
                        .requestsPerSec(r.getRequestsPerSec())
                        .errorRatePct(r.getErrorRatePct())
                        .totalRequests(r.getTotalRequests())
                        .totalFailures(r.getTotalFailures())
                        .passedGate(r.getPassedGate())
                        .testedAt(r.getTestedAt())
                        .build())
                .toList();

        return ResponseEntity.ok(response);
    }
}

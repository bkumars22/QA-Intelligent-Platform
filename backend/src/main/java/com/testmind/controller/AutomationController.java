package com.testmind.controller;

import com.testmind.dto.*;
import com.testmind.model.GeneratedReport;
import com.testmind.service.AutomationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

// ─── DTOs used only in this controller ───────────────────────────────────────
record FileSaveRequest(String path, String content, String sha, String commitMessage) {}
record ExecuteFromFrameworkRequest(List<String> testNames, boolean allTests) {}

@RestController
@RequestMapping("/api/automation")
public class AutomationController {

    private final AutomationService service;

    public AutomationController(AutomationService service) {
        this.service = service;
    }

    // ─── Framework ────────────────────────────────────────────────────────────

    @GetMapping("/projects/{projectId}/frameworks")
    public ResponseEntity<List<FrameworkProfileResponse>> getFrameworks(@PathVariable Long projectId) {
        return ResponseEntity.ok(service.getFrameworkProfiles(projectId));
    }

    @PostMapping("/frameworks/connect")
    public ResponseEntity<FrameworkProfileResponse> connectFramework(
            @Valid @RequestBody ConnectFrameworkRequest req) {
        return ResponseEntity.ok(service.connectFramework(req));
    }

    // ─── Code Generation ─────────────────────────────────────────────────────

    @PostMapping("/generate-code")
    public ResponseEntity<AutomationExecutionResponse> generateCode(
            @Valid @RequestBody GenerateAutomationRequest req) {
        return ResponseEntity.ok(service.generateAutomationCode(req));
    }

    // ─── Execution ───────────────────────────────────────────────────────────

    @PostMapping("/execute/{executionId}")
    public ResponseEntity<AutomationExecutionResponse> execute(
            @PathVariable Long executionId,
            @RequestParam(required = false) String appUrl) {
        return ResponseEntity.ok(service.startExecution(executionId, appUrl));
    }

    @GetMapping("/projects/{projectId}/executions")
    public ResponseEntity<List<AutomationExecutionResponse>> getExecutions(@PathVariable Long projectId) {
        return ResponseEntity.ok(service.getExecutions(projectId));
    }

    @GetMapping("/executions/{id}")
    public ResponseEntity<AutomationExecutionResponse> getExecution(@PathVariable Long id) {
        return ResponseEntity.ok(service.getExecution(id));
    }

    @GetMapping("/executions/{id}/results")
    public ResponseEntity<List<Map<String, Object>>> getResults(@PathVariable Long id) {
        return ResponseEntity.ok(service.getResults(id));
    }

    // ─── Reports ─────────────────────────────────────────────────────────────

    @GetMapping("/projects/{projectId}/reports")
    public ResponseEntity<List<Map<String, Object>>> getReports(@PathVariable Long projectId) {
        return ResponseEntity.ok(service.getReports(projectId));
    }

    @GetMapping("/reports/{token}")
    public ResponseEntity<String> getReportHtml(@PathVariable String token) {
        return service.getReportByToken(token)
                .map(r -> ResponseEntity.ok()
                        .contentType(MediaType.TEXT_HTML)
                        .header(HttpHeaders.CONTENT_DISPOSITION, "inline")
                        .body(r.getHtmlContent()))
                .orElse(ResponseEntity.notFound().build());
    }

    // ─── Framework File Explorer ─────────────────────────────────────────────

    @GetMapping("/frameworks/{profileId}/file-tree")
    public ResponseEntity<List<Map<String, Object>>> getFileTree(@PathVariable Long profileId) {
        return ResponseEntity.ok(service.getFileTree(profileId));
    }

    @GetMapping("/frameworks/{profileId}/file-content")
    public ResponseEntity<Map<String, Object>> getFileContent(
            @PathVariable Long profileId,
            @RequestParam String path) {
        return ResponseEntity.ok(service.getFileContent(profileId, path));
    }

    @PutMapping("/frameworks/{profileId}/file-content")
    public ResponseEntity<Map<String, Object>> saveFileContent(
            @PathVariable Long profileId,
            @RequestBody FileSaveRequest req) {
        return ResponseEntity.ok(service.saveFileContent(profileId, req.path(), req.content(), req.sha(), req.commitMessage()));
    }

    @PostMapping("/frameworks/{profileId}/execute")
    public ResponseEntity<AutomationExecutionResponse> executeFromFramework(
            @PathVariable Long profileId,
            @RequestBody ExecuteFromFrameworkRequest req) {
        return ResponseEntity.ok(service.executeFromFramework(profileId, req.testNames(), req.allTests()));
    }

    // ─── Reports ─────────────────────────────────────────────────────────────

    @GetMapping("/reports/{token}/download")
    public ResponseEntity<byte[]> downloadReport(@PathVariable String token) {
        return service.getReportByToken(token)
                .map(r -> ResponseEntity.ok()
                        .contentType(MediaType.TEXT_HTML)
                        .header(HttpHeaders.CONTENT_DISPOSITION,
                                "attachment; filename=\"qa-report-" + token.substring(0, 8) + ".html\"")
                        .body(r.getHtmlContent().getBytes()))
                .orElse(ResponseEntity.notFound().build());
    }
}

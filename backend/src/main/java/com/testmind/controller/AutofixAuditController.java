package com.testmind.controller;

import com.testmind.dto.AutofixAuditIngestRequest;
import com.testmind.dto.AutofixAuditResponse;
import com.testmind.service.AutofixAuditService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/autofix-audit")
@RequiredArgsConstructor
@Tag(name = "Autofix Audit", description = "CodegenerateAgent auto-fix attempt history")
public class AutofixAuditController {

    private final AutofixAuditService autofixAuditService;

    /**
     * Called by the Python AI engine after apply_and_verify_fixes — not a logged-in
     * user, guarded internally by SecurityConfig permitAll like other AI-engine callbacks
     * (e.g. /api/pipeline/callback, /api/webhook/github).
     */
    @PostMapping
    @Operation(summary = "Ingest a run's auto-fix attempts")
    public ResponseEntity<Void> ingest(@RequestBody AutofixAuditIngestRequest request) {
        autofixAuditService.ingest(request);
        return ResponseEntity.ok().build();
    }

    @GetMapping
    @Operation(summary = "List auto-fix attempts, optionally filtered by project or status")
    public ResponseEntity<List<AutofixAuditResponse>> list(
            @RequestParam(required = false) Long projectId,
            @RequestParam(required = false) String status) {
        return ResponseEntity.ok(autofixAuditService.list(projectId, status));
    }
}

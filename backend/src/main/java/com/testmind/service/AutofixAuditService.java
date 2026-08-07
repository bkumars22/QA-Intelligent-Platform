package com.testmind.service;

import com.testmind.dto.AutofixAuditIngestRequest;
import com.testmind.dto.AutofixAuditResponse;
import com.testmind.model.AutofixAudit;
import com.testmind.repository.AutofixAuditRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AutofixAuditService {

    private final AutofixAuditRepository autofixAuditRepository;

    @Transactional
    public void ingest(AutofixAuditIngestRequest request) {
        if (request.getEntries() == null) {
            return;
        }
        for (AutofixAuditIngestRequest.Entry entry : request.getEntries()) {
            AutofixAudit audit = AutofixAudit.builder()
                    .runId(request.getRunId())
                    .projectId(request.getProjectId())
                    .repoUrl(request.getRepoUrl())
                    .commitSha(request.getCommitSha())
                    .filePath(entry.getFilePath())
                    .defectTitle(entry.getDefectTitle())
                    .severity(entry.getSeverity())
                    .branch(entry.getBranch())
                    .why(entry.getWhy())
                    .testsPassed(entry.getTestsPassed())
                    .status(entry.getStatus())
                    .prUrl(entry.getPrUrl())
                    .detail(entry.getDetail())
                    .build();
            autofixAuditRepository.save(audit);
        }
    }

    @Transactional(readOnly = true)
    public List<AutofixAuditResponse> list(Long projectId, String status) {
        List<AutofixAudit> rows;
        if (projectId != null && status != null) {
            rows = autofixAuditRepository.findByProjectIdAndStatusOrderByCreatedAtDesc(projectId, status);
        } else if (projectId != null) {
            rows = autofixAuditRepository.findByProjectIdOrderByCreatedAtDesc(projectId);
        } else if (status != null) {
            rows = autofixAuditRepository.findByStatusOrderByCreatedAtDesc(status);
        } else {
            rows = autofixAuditRepository.findAllByOrderByCreatedAtDesc();
        }
        return rows.stream().map(this::toResponse).toList();
    }

    private AutofixAuditResponse toResponse(AutofixAudit a) {
        AutofixAuditResponse r = new AutofixAuditResponse();
        r.setId(a.getId());
        r.setRunId(a.getRunId());
        r.setProjectId(a.getProjectId());
        r.setRepoUrl(a.getRepoUrl());
        r.setCommitSha(a.getCommitSha());
        r.setFilePath(a.getFilePath());
        r.setDefectTitle(a.getDefectTitle());
        r.setSeverity(a.getSeverity());
        r.setBranch(a.getBranch());
        r.setWhy(a.getWhy());
        r.setTestsPassed(a.getTestsPassed());
        r.setStatus(a.getStatus());
        r.setPrUrl(a.getPrUrl());
        r.setDetail(a.getDetail());
        r.setCreatedAt(a.getCreatedAt());
        return r;
    }
}

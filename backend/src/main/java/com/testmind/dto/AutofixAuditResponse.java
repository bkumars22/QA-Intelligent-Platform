package com.testmind.dto;

import lombok.Data;

import java.time.OffsetDateTime;

@Data
public class AutofixAuditResponse {
    private Long id;
    private String runId;
    private Long projectId;
    private String repoUrl;
    private String commitSha;
    private String filePath;
    private String defectTitle;
    private String severity;
    private String branch;
    private String why;
    private Boolean testsPassed;
    private String status;
    private String prUrl;
    private String detail;
    private OffsetDateTime createdAt;
}

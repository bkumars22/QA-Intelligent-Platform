package com.testmind.dto;

import com.testmind.model.AutomationExecution;
import java.time.OffsetDateTime;

public class AutomationExecutionResponse {
    private Long id;
    private Long projectId;
    private Long frameworkProfileId;
    private String suiteName;
    private String frameworkType;
    private String appUrl;
    private String generatedCode;
    private String status;
    private int totalTests;
    private int passed;
    private int failed;
    private int skipped;
    private Long durationMs;
    private String triggeredBy;
    private String commitSha;
    private String reportUrl;
    private OffsetDateTime startedAt;
    private OffsetDateTime completedAt;
    private OffsetDateTime createdAt;

    public static AutomationExecutionResponse from(AutomationExecution e) {
        AutomationExecutionResponse r = new AutomationExecutionResponse();
        r.id = e.getId();
        r.projectId = e.getProjectId();
        r.frameworkProfileId = e.getFrameworkProfileId();
        r.suiteName = e.getSuiteName();
        r.frameworkType = e.getFrameworkType().name();
        r.appUrl = e.getAppUrl();
        r.generatedCode = e.getGeneratedCode();
        r.status = e.getStatus().name();
        r.totalTests = e.getTotalTests();
        r.passed = e.getPassed();
        r.failed = e.getFailed();
        r.skipped = e.getSkipped();
        r.durationMs = e.getDurationMs();
        r.triggeredBy = e.getTriggeredBy();
        r.commitSha = e.getCommitSha();
        r.reportUrl = e.getReportUrl();
        r.startedAt = e.getStartedAt();
        r.completedAt = e.getCompletedAt();
        r.createdAt = e.getCreatedAt();
        return r;
    }

    public Long getId() { return id; }
    public Long getProjectId() { return projectId; }
    public Long getFrameworkProfileId() { return frameworkProfileId; }
    public String getSuiteName() { return suiteName; }
    public String getFrameworkType() { return frameworkType; }
    public String getAppUrl() { return appUrl; }
    public String getGeneratedCode() { return generatedCode; }
    public String getStatus() { return status; }
    public int getTotalTests() { return totalTests; }
    public int getPassed() { return passed; }
    public int getFailed() { return failed; }
    public int getSkipped() { return skipped; }
    public Long getDurationMs() { return durationMs; }
    public String getTriggeredBy() { return triggeredBy; }
    public String getCommitSha() { return commitSha; }
    public String getReportUrl() { return reportUrl; }
    public OffsetDateTime getStartedAt() { return startedAt; }
    public OffsetDateTime getCompletedAt() { return completedAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
}

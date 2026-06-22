package com.testmind.model;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "automation_executions")
public class AutomationExecution {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "framework_profile_id")
    private Long frameworkProfileId;

    @Column(name = "suite_name", nullable = false, length = 255)
    private String suiteName;

    @Enumerated(EnumType.STRING)
    @Column(name = "framework_type", nullable = false, length = 20)
    private FrameworkType frameworkType;

    @Column(name = "app_url", length = 500)
    private String appUrl;

    @Column(name = "generated_code", columnDefinition = "TEXT")
    private String generatedCode;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private AutomationStatus status = AutomationStatus.QUEUED;

    @Column(name = "total_tests")
    private int totalTests;

    @Column(name = "passed")
    private int passed;

    @Column(name = "failed")
    private int failed;

    @Column(name = "skipped")
    private int skipped;

    @Column(name = "duration_ms")
    private Long durationMs;

    @Column(name = "triggered_by", length = 255)
    private String triggeredBy;

    @Column(name = "commit_sha", length = 40)
    private String commitSha;

    @Column(name = "report_url", length = 500)
    private String reportUrl;

    @Column(name = "started_at")
    private OffsetDateTime startedAt;

    @Column(name = "completed_at")
    private OffsetDateTime completedAt;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @PrePersist
    void onCreate() { createdAt = OffsetDateTime.now(); }

    public Long getId() { return id; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long v) { projectId = v; }
    public Long getFrameworkProfileId() { return frameworkProfileId; }
    public void setFrameworkProfileId(Long v) { frameworkProfileId = v; }
    public String getSuiteName() { return suiteName; }
    public void setSuiteName(String v) { suiteName = v; }
    public FrameworkType getFrameworkType() { return frameworkType; }
    public void setFrameworkType(FrameworkType v) { frameworkType = v; }
    public String getAppUrl() { return appUrl; }
    public void setAppUrl(String v) { appUrl = v; }
    public String getGeneratedCode() { return generatedCode; }
    public void setGeneratedCode(String v) { generatedCode = v; }
    public AutomationStatus getStatus() { return status; }
    public void setStatus(AutomationStatus v) { status = v; }
    public int getTotalTests() { return totalTests; }
    public void setTotalTests(int v) { totalTests = v; }
    public int getPassed() { return passed; }
    public void setPassed(int v) { passed = v; }
    public int getFailed() { return failed; }
    public void setFailed(int v) { failed = v; }
    public int getSkipped() { return skipped; }
    public void setSkipped(int v) { skipped = v; }
    public Long getDurationMs() { return durationMs; }
    public void setDurationMs(Long v) { durationMs = v; }
    public String getTriggeredBy() { return triggeredBy; }
    public void setTriggeredBy(String v) { triggeredBy = v; }
    public String getCommitSha() { return commitSha; }
    public void setCommitSha(String v) { commitSha = v; }
    public String getReportUrl() { return reportUrl; }
    public void setReportUrl(String v) { reportUrl = v; }
    public OffsetDateTime getStartedAt() { return startedAt; }
    public void setStartedAt(OffsetDateTime v) { startedAt = v; }
    public OffsetDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(OffsetDateTime v) { completedAt = v; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
}

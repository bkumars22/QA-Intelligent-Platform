package com.testmind.model;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "automation_results")
public class AutomationResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "execution_id", nullable = false)
    private Long executionId;

    @Column(name = "test_name", nullable = false, length = 500)
    private String testName;

    @Column(name = "test_class", length = 500)
    private String testClass;

    @Column(name = "status", nullable = false, length = 20)
    private String status;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "stack_trace", columnDefinition = "TEXT")
    private String stackTrace;

    @Column(name = "screenshot_base64", columnDefinition = "TEXT")
    private String screenshotBase64;

    @Column(name = "ai_explanation", columnDefinition = "TEXT")
    private String aiExplanation;

    @Column(name = "jira_ticket_key", length = 50)
    private String jiraTicketKey;

    @Column(name = "jira_ticket_url", length = 500)
    private String jiraTicketUrl;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @PrePersist
    void onCreate() { createdAt = OffsetDateTime.now(); }

    public Long getId() { return id; }
    public Long getExecutionId() { return executionId; }
    public void setExecutionId(Long v) { executionId = v; }
    public String getTestName() { return testName; }
    public void setTestName(String v) { testName = v; }
    public String getTestClass() { return testClass; }
    public void setTestClass(String v) { testClass = v; }
    public String getStatus() { return status; }
    public void setStatus(String v) { status = v; }
    public Integer getDurationMs() { return durationMs; }
    public void setDurationMs(Integer v) { durationMs = v; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String v) { errorMessage = v; }
    public String getStackTrace() { return stackTrace; }
    public void setStackTrace(String v) { stackTrace = v; }
    public String getScreenshotBase64() { return screenshotBase64; }
    public void setScreenshotBase64(String v) { screenshotBase64 = v; }
    public String getAiExplanation() { return aiExplanation; }
    public void setAiExplanation(String v) { aiExplanation = v; }
    public String getJiraTicketKey() { return jiraTicketKey; }
    public void setJiraTicketKey(String v) { jiraTicketKey = v; }
    public String getJiraTicketUrl() { return jiraTicketUrl; }
    public void setJiraTicketUrl(String v) { jiraTicketUrl = v; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
}

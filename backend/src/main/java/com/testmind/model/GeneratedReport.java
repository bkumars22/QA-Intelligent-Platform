package com.testmind.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.OffsetDateTime;

@Entity
@Table(name = "generated_reports")
public class GeneratedReport {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "execution_id", nullable = false)
    private Long executionId;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Column(name = "title", nullable = false, length = 500)
    private String title;

    @Column(name = "html_content", nullable = false, columnDefinition = "TEXT")
    private String htmlContent;

    @Column(name = "total_tests")
    private int totalTests;

    @Column(name = "passed")
    private int passed;

    @Column(name = "failed")
    private int failed;

    @Column(name = "pass_rate", precision = 5, scale = 2)
    private BigDecimal passRate;

    @Column(name = "execution_date")
    private OffsetDateTime executionDate;

    @Column(name = "share_token", unique = true, length = 64)
    private String shareToken;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @PrePersist
    void onCreate() { createdAt = OffsetDateTime.now(); }

    public Long getId() { return id; }
    public Long getExecutionId() { return executionId; }
    public void setExecutionId(Long v) { executionId = v; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long v) { projectId = v; }
    public String getTitle() { return title; }
    public void setTitle(String v) { title = v; }
    public String getHtmlContent() { return htmlContent; }
    public void setHtmlContent(String v) { htmlContent = v; }
    public int getTotalTests() { return totalTests; }
    public void setTotalTests(int v) { totalTests = v; }
    public int getPassed() { return passed; }
    public void setPassed(int v) { passed = v; }
    public int getFailed() { return failed; }
    public void setFailed(int v) { failed = v; }
    public BigDecimal getPassRate() { return passRate; }
    public void setPassRate(BigDecimal v) { passRate = v; }
    public OffsetDateTime getExecutionDate() { return executionDate; }
    public void setExecutionDate(OffsetDateTime v) { executionDate = v; }
    public String getShareToken() { return shareToken; }
    public void setShareToken(String v) { shareToken = v; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
}

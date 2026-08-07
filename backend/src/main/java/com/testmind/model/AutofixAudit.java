package com.testmind.model;

import jakarta.persistence.*;
import lombok.*;

import java.time.OffsetDateTime;

@Entity
@Table(name = "autofix_audit")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AutofixAudit {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "run_id", nullable = false, length = 100)
    private String runId;

    @Column(name = "project_id")
    private Long projectId;

    @Column(name = "repo_url", columnDefinition = "TEXT")
    private String repoUrl;

    @Column(name = "commit_sha", length = 64)
    private String commitSha;

    @Column(name = "file_path", nullable = false, columnDefinition = "TEXT")
    private String filePath;

    @Column(name = "defect_title", nullable = false, length = 500)
    private String defectTitle;

    @Column(length = 10)
    private String severity;

    @Column(length = 200)
    private String branch;

    @Column(columnDefinition = "TEXT")
    private String why;

    @Column(name = "tests_passed")
    private Boolean testsPassed;

    @Column(nullable = false, length = 30)
    private String status;

    @Column(name = "pr_url", columnDefinition = "TEXT")
    private String prUrl;

    @Column(columnDefinition = "TEXT")
    private String detail;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        if (this.createdAt == null) {
            this.createdAt = OffsetDateTime.now();
        }
    }
}

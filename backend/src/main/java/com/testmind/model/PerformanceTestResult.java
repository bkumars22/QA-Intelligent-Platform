package com.testmind.model;

import jakarta.persistence.*;
import lombok.*;

import java.time.OffsetDateTime;

@Entity
@Table(name = "performance_test_results")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceTestResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 20)
    private String system;

    @Column(name = "build_sha", nullable = false, length = 64)
    private String buildSha;

    @Column(nullable = false, length = 255)
    private String endpoint;

    @Column(name = "p50_ms", nullable = false)
    private Double p50Ms;

    @Column(name = "p95_ms", nullable = false)
    private Double p95Ms;

    @Column(name = "p99_ms", nullable = false)
    private Double p99Ms;

    @Column(name = "requests_per_sec", nullable = false)
    private Double requestsPerSec;

    @Column(name = "error_rate_pct", nullable = false)
    private Double errorRatePct;

    @Column(name = "total_requests", nullable = false)
    private Integer totalRequests;

    @Column(name = "total_failures", nullable = false)
    private Integer totalFailures;

    @Column(name = "passed_gate", nullable = false)
    private Boolean passedGate;

    @Column(name = "tested_at", nullable = false)
    @Builder.Default
    private OffsetDateTime testedAt = OffsetDateTime.now();
}

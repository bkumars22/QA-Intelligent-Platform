package com.testmind.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceResultResponse {

    private Long id;
    private String system;
    private String buildSha;
    private String endpoint;
    private Double p50Ms;
    private Double p95Ms;
    private Double p99Ms;
    private Double requestsPerSec;
    private Double errorRatePct;
    private Integer totalRequests;
    private Integer totalFailures;
    private Boolean passedGate;
    private OffsetDateTime testedAt;
}

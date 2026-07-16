package com.testmind.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class PerformanceResultRequest {

    @NotBlank
    private String system;

    @NotBlank
    private String buildSha;

    @NotBlank
    private String endpoint;

    @NotNull
    private Double p50Ms;

    @NotNull
    private Double p95Ms;

    @NotNull
    private Double p99Ms;

    @NotNull
    private Double requestsPerSec;

    @NotNull
    private Double errorRatePct;

    @NotNull
    private Integer totalRequests;

    @NotNull
    private Integer totalFailures;

    @NotNull
    private Boolean passedGate;
}

package com.testmind.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class PerformanceRunRequest {

    @NotBlank
    private String system;

    @NotBlank
    private String host;

    private Integer users = 50;

    private String runTime = "2m";
}

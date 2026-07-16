package com.testmind.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExecutionResultResponse {

    private Long id;
    private Long testCaseId;
    private String testCaseTitle;
    private String status;
    private Integer durationMs;
    private String screenshotUrl;
    private String errorMessage;
    private String aiExplanation;
    private Double deepevalScore;
}

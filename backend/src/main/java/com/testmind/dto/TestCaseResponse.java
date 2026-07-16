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
public class TestCaseResponse {

    private Long id;
    private Long pipelineRunId;
    private String title;
    private String testType;
    private String gapCategory;
    private String preconditions;
    private String testSteps;
    private String expectedResult;
    private String priority;
    private String status;
    private String reviewerNotes;
    private OffsetDateTime reviewedAt;
}

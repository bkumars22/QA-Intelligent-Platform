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
public class StoryAnalysisResponse {

    private Long id;
    private String jiraStoryId;
    private String jiraSummary;
    private String businessRules;
    private String acceptanceCriteria;
    private String edgeCases;
    private String dataRules;
    private OffsetDateTime analyzedAt;
}

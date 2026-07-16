package com.testmind.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GapReportResponse {

    private Long id;
    private String gapCategory;
    private String description;
    private Double priorityScore;
    private String affectedRequirement;
}

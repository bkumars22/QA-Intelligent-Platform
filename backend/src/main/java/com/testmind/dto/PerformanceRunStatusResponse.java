package com.testmind.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceRunStatusResponse {

    private String status;       // "not_found" | "queued" | "in_progress" | "completed"
    private String conclusion;   // null while running; "success" | "failure" | ... once completed
    private String runUrl;       // link to the GitHub Actions run, once found
}

package com.testmind.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceRunResponse {

    private boolean dispatched;
    private String dispatchedAt;   // ISO-8601 -- pass back to /run/status to correlate the resulting run
    private String message;
}

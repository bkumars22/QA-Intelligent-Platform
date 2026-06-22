package com.testmind.dto;

import jakarta.validation.constraints.NotNull;

public class ExecuteAutomationRequest {
    @NotNull
    private Long executionId;
    private String appUrl;

    public Long getExecutionId() { return executionId; }
    public void setExecutionId(Long v) { executionId = v; }
    public String getAppUrl() { return appUrl; }
    public void setAppUrl(String v) { appUrl = v; }
}

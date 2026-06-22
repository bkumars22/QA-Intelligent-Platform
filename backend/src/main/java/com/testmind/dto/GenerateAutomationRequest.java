package com.testmind.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public class GenerateAutomationRequest {
    @NotNull
    private Long projectId;
    @NotNull
    private Long frameworkProfileId;
    @NotBlank
    private String suiteName;
    private List<String> testCaseTitles;
    private List<String> testCaseDescriptions;

    public Long getProjectId() { return projectId; }
    public void setProjectId(Long v) { projectId = v; }
    public Long getFrameworkProfileId() { return frameworkProfileId; }
    public void setFrameworkProfileId(Long v) { frameworkProfileId = v; }
    public String getSuiteName() { return suiteName; }
    public void setSuiteName(String v) { suiteName = v; }
    public List<String> getTestCaseTitles() { return testCaseTitles; }
    public void setTestCaseTitles(List<String> v) { testCaseTitles = v; }
    public List<String> getTestCaseDescriptions() { return testCaseDescriptions; }
    public void setTestCaseDescriptions(List<String> v) { testCaseDescriptions = v; }
}

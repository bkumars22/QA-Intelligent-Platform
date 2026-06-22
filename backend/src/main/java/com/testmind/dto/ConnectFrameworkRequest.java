package com.testmind.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class ConnectFrameworkRequest {
    @NotNull
    private Long projectId;
    @NotBlank
    private String frameworkType;   // PLAYWRIGHT | SELENIUM
    @NotBlank
    private String repoUrl;
    private String branch = "main";
    private String githubToken;

    public Long getProjectId() { return projectId; }
    public void setProjectId(Long v) { projectId = v; }
    public String getFrameworkType() { return frameworkType; }
    public void setFrameworkType(String v) { frameworkType = v; }
    public String getRepoUrl() { return repoUrl; }
    public void setRepoUrl(String v) { repoUrl = v; }
    public String getBranch() { return branch; }
    public void setBranch(String v) { branch = v; }
    public String getGithubToken() { return githubToken; }
    public void setGithubToken(String v) { githubToken = v; }
}

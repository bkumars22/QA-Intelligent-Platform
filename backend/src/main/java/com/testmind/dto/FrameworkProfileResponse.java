package com.testmind.dto;

import com.testmind.model.FrameworkProfile;
import java.time.OffsetDateTime;

public class FrameworkProfileResponse {
    private Long id;
    private Long projectId;
    private String frameworkType;
    private String repoUrl;
    private String branch;
    private String status;
    private String errorMessage;
    private String baseClass;
    private String folderStructure;
    private String namingConventions;
    private String importPatterns;
    private String hookPatterns;
    private String customUtilities;
    private Integer pageObjectsCount;
    private Integer testFilesCount;
    private String summaryText;
    private OffsetDateTime analysedAt;
    private OffsetDateTime createdAt;

    public static FrameworkProfileResponse from(FrameworkProfile p) {
        FrameworkProfileResponse r = new FrameworkProfileResponse();
        r.id = p.getId();
        r.projectId = p.getProjectId();
        r.frameworkType = p.getFrameworkType().name();
        r.repoUrl = p.getRepoUrl();
        r.branch = p.getBranch();
        r.status = p.getStatus().name();
        r.errorMessage = p.getErrorMessage();
        r.baseClass = p.getBaseClass();
        r.folderStructure = p.getFolderStructure();
        r.namingConventions = p.getNamingConventions();
        r.importPatterns = p.getImportPatterns();
        r.hookPatterns = p.getHookPatterns();
        r.customUtilities = p.getCustomUtilities();
        r.pageObjectsCount = p.getPageObjectsCount();
        r.testFilesCount = p.getTestFilesCount();
        r.summaryText = p.getSummaryText();
        r.analysedAt = p.getAnalysedAt();
        r.createdAt = p.getCreatedAt();
        return r;
    }

    public Long getId() { return id; }
    public Long getProjectId() { return projectId; }
    public String getFrameworkType() { return frameworkType; }
    public String getRepoUrl() { return repoUrl; }
    public String getBranch() { return branch; }
    public String getStatus() { return status; }
    public String getErrorMessage() { return errorMessage; }
    public String getBaseClass() { return baseClass; }
    public String getFolderStructure() { return folderStructure; }
    public String getNamingConventions() { return namingConventions; }
    public String getImportPatterns() { return importPatterns; }
    public String getHookPatterns() { return hookPatterns; }
    public String getCustomUtilities() { return customUtilities; }
    public Integer getPageObjectsCount() { return pageObjectsCount; }
    public Integer getTestFilesCount() { return testFilesCount; }
    public String getSummaryText() { return summaryText; }
    public OffsetDateTime getAnalysedAt() { return analysedAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
}

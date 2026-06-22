package com.testmind.model;

import jakarta.persistence.*;
import java.time.OffsetDateTime;

@Entity
@Table(name = "framework_profiles")
public class FrameworkProfile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "project_id", nullable = false)
    private Long projectId;

    @Enumerated(EnumType.STRING)
    @Column(name = "framework_type", nullable = false, length = 20)
    private FrameworkType frameworkType;

    @Column(name = "repo_url", nullable = false, length = 500)
    private String repoUrl;

    @Column(name = "branch", length = 100)
    private String branch = "main";

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 20)
    private FrameworkConnectionStatus status = FrameworkConnectionStatus.PENDING;

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "base_class", length = 500)
    private String baseClass;

    @Column(name = "folder_structure", columnDefinition = "jsonb")
    private String folderStructure;

    @Column(name = "naming_conventions", columnDefinition = "jsonb")
    private String namingConventions;

    @Column(name = "import_patterns", columnDefinition = "jsonb")
    private String importPatterns;

    @Column(name = "hook_patterns", columnDefinition = "jsonb")
    private String hookPatterns;

    @Column(name = "custom_utilities", columnDefinition = "jsonb")
    private String customUtilities;

    @Column(name = "page_objects_count")
    private Integer pageObjectsCount;

    @Column(name = "test_files_count")
    private Integer testFilesCount;

    @Column(name = "summary_text", columnDefinition = "TEXT")
    private String summaryText;

    @Column(name = "analysed_at")
    private OffsetDateTime analysedAt;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    @Column(name = "updated_at")
    private OffsetDateTime updatedAt;

    @PrePersist
    void onCreate() {
        createdAt = OffsetDateTime.now();
        updatedAt = OffsetDateTime.now();
    }

    @PreUpdate
    void onUpdate() { updatedAt = OffsetDateTime.now(); }

    public Long getId() { return id; }
    public Long getProjectId() { return projectId; }
    public void setProjectId(Long projectId) { this.projectId = projectId; }
    public FrameworkType getFrameworkType() { return frameworkType; }
    public void setFrameworkType(FrameworkType frameworkType) { this.frameworkType = frameworkType; }
    public String getRepoUrl() { return repoUrl; }
    public void setRepoUrl(String repoUrl) { this.repoUrl = repoUrl; }
    public String getBranch() { return branch; }
    public void setBranch(String branch) { this.branch = branch; }
    public FrameworkConnectionStatus getStatus() { return status; }
    public void setStatus(FrameworkConnectionStatus status) { this.status = status; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
    public String getBaseClass() { return baseClass; }
    public void setBaseClass(String baseClass) { this.baseClass = baseClass; }
    public String getFolderStructure() { return folderStructure; }
    public void setFolderStructure(String folderStructure) { this.folderStructure = folderStructure; }
    public String getNamingConventions() { return namingConventions; }
    public void setNamingConventions(String namingConventions) { this.namingConventions = namingConventions; }
    public String getImportPatterns() { return importPatterns; }
    public void setImportPatterns(String importPatterns) { this.importPatterns = importPatterns; }
    public String getHookPatterns() { return hookPatterns; }
    public void setHookPatterns(String hookPatterns) { this.hookPatterns = hookPatterns; }
    public String getCustomUtilities() { return customUtilities; }
    public void setCustomUtilities(String customUtilities) { this.customUtilities = customUtilities; }
    public Integer getPageObjectsCount() { return pageObjectsCount; }
    public void setPageObjectsCount(Integer pageObjectsCount) { this.pageObjectsCount = pageObjectsCount; }
    public Integer getTestFilesCount() { return testFilesCount; }
    public void setTestFilesCount(Integer testFilesCount) { this.testFilesCount = testFilesCount; }
    public String getSummaryText() { return summaryText; }
    public void setSummaryText(String summaryText) { this.summaryText = summaryText; }
    public OffsetDateTime getAnalysedAt() { return analysedAt; }
    public void setAnalysedAt(OffsetDateTime analysedAt) { this.analysedAt = analysedAt; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public OffsetDateTime getUpdatedAt() { return updatedAt; }
}

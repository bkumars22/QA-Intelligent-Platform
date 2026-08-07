package com.testmind.dto;

import lombok.Data;

import java.util.List;

@Data
public class AutofixAuditIngestRequest {
    private String runId;
    private Long projectId;
    private String repoUrl;
    private String commitSha;
    private List<Entry> entries;

    @Data
    public static class Entry {
        private String filePath;
        private String defectTitle;
        private String severity;
        private String branch;
        private String why;
        private Boolean testsPassed;
        private String status;
        private String prUrl;
        private String detail;
    }
}

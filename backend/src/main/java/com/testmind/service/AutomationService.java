package com.testmind.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.testmind.dto.*;
import com.testmind.model.*;
import com.testmind.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.OffsetDateTime;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class AutomationService {

    private static final Logger log = LoggerFactory.getLogger(AutomationService.class);

    private final FrameworkProfileRepository frameworkRepo;
    private final AutomationExecutionRepository executionRepo;
    private final AutomationResultRepository resultRepo;
    private final GeneratedReportRepository reportRepo;
    private final AutomationAiClient aiClient;
    private final SimpMessagingTemplate ws;
    private final ObjectMapper mapper = new ObjectMapper();
    private final HttpClient http = HttpClient.newBuilder().build();

    public AutomationService(
            FrameworkProfileRepository frameworkRepo,
            AutomationExecutionRepository executionRepo,
            AutomationResultRepository resultRepo,
            GeneratedReportRepository reportRepo,
            AutomationAiClient aiClient,
            SimpMessagingTemplate ws) {
        this.frameworkRepo = frameworkRepo;
        this.executionRepo = executionRepo;
        this.resultRepo = resultRepo;
        this.reportRepo = reportRepo;
        this.aiClient = aiClient;
        this.ws = ws;
    }

    // ─── Framework Profile ────────────────────────────────────────────────────

    public List<FrameworkProfileResponse> getFrameworkProfiles(Long projectId) {
        return frameworkRepo.findByProjectId(projectId).stream()
                .map(FrameworkProfileResponse::from).toList();
    }

    @Transactional
    public FrameworkProfileResponse connectFramework(ConnectFrameworkRequest req) {
        FrameworkType type = FrameworkType.valueOf(req.getFrameworkType().toUpperCase());

        FrameworkProfile profile = frameworkRepo
                .findByProjectIdAndFrameworkType(req.getProjectId(), type)
                .orElse(new FrameworkProfile());

        profile.setProjectId(req.getProjectId());
        profile.setFrameworkType(type);
        profile.setRepoUrl(req.getRepoUrl());
        profile.setBranch(req.getBranch() != null ? req.getBranch() : "main");
        profile.setStatus(FrameworkConnectionStatus.ANALYSING);
        profile.setErrorMessage(null);
        if (req.getGithubToken() != null && !req.getGithubToken().isBlank()) {
            profile.setGithubToken(req.getGithubToken());
        }
        profile = frameworkRepo.save(profile);

        analyseFrameworkAsync(profile.getId(), req.getRepoUrl(), req.getBranch(), req.getGithubToken(), type);
        return FrameworkProfileResponse.from(profile);
    }

    @Async
    @Transactional
    public void analyseFrameworkAsync(Long profileId, String repoUrl, String branch, String token, FrameworkType type) {
        FrameworkProfile profile = frameworkRepo.findById(profileId).orElseThrow();
        try {
            Map<String, Object> result = aiClient.analyseFramework(repoUrl, branch, token, type.name().toLowerCase());

            profile.setBaseClass((String) result.getOrDefault("base_class", ""));
            profile.setFolderStructure(toJson(result.get("folder_structure")));
            profile.setNamingConventions(toJson(result.get("naming_conventions")));
            profile.setImportPatterns(toJson(result.get("import_patterns")));
            profile.setHookPatterns(toJson(result.get("hook_patterns")));
            profile.setCustomUtilities(toJson(result.get("custom_utilities")));
            profile.setSummaryText((String) result.getOrDefault("summary", ""));
            Object poc = result.get("page_objects_count");
            if (poc instanceof Number n) profile.setPageObjectsCount(n.intValue());
            Object tfc = result.get("test_files_count");
            if (tfc instanceof Number n) profile.setTestFilesCount(n.intValue());
            profile.setStatus(FrameworkConnectionStatus.CONNECTED);
            profile.setAnalysedAt(OffsetDateTime.now());
        } catch (Exception e) {
            log.error("Framework analysis failed for profile {}: {}", profileId, e.getMessage());
            profile.setStatus(FrameworkConnectionStatus.FAILED);
            profile.setErrorMessage(e.getMessage());
        }
        frameworkRepo.save(profile);

        ws.convertAndSend("/topic/framework/" + profile.getProjectId(),
                FrameworkProfileResponse.from(profile));
    }

    // ─── Code Generation ─────────────────────────────────────────────────────

    @Transactional
    public AutomationExecutionResponse generateAutomationCode(GenerateAutomationRequest req) {
        FrameworkProfile fp = frameworkRepo.findById(req.getFrameworkProfileId())
                .orElseThrow(() -> new RuntimeException("Framework profile not found"));

        AutomationExecution exec = new AutomationExecution();
        exec.setProjectId(req.getProjectId());
        exec.setFrameworkProfileId(fp.getId());
        exec.setSuiteName(req.getSuiteName());
        exec.setFrameworkType(fp.getFrameworkType());
        exec.setStatus(AutomationStatus.QUEUED);
        exec = executionRepo.save(exec);

        generateCodeAsync(exec.getId(), fp, req.getTestCaseTitles(), req.getTestCaseDescriptions());
        return AutomationExecutionResponse.from(exec);
    }

    @Async
    @Transactional
    public void generateCodeAsync(Long execId, FrameworkProfile fp, List<String> titles, List<String> descriptions) {
        AutomationExecution exec = executionRepo.findById(execId).orElseThrow();
        try {
            String code = aiClient.generateCode(fp, titles, descriptions);
            exec.setGeneratedCode(code);
            exec.setTotalTests(titles != null ? titles.size() : 0);
        } catch (Exception e) {
            log.error("Code generation failed for exec {}: {}", execId, e.getMessage());
            exec.setStatus(AutomationStatus.ERROR);
        }
        executionRepo.save(exec);
        ws.convertAndSend("/topic/execution/" + exec.getProjectId(),
                AutomationExecutionResponse.from(exec));
    }

    // ─── Execution ───────────────────────────────────────────────────────────

    @Transactional
    public AutomationExecutionResponse startExecution(Long executionId, String appUrl) {
        AutomationExecution exec = executionRepo.findById(executionId).orElseThrow();
        exec.setStatus(AutomationStatus.RUNNING);
        exec.setStartedAt(OffsetDateTime.now());
        if (appUrl != null) exec.setAppUrl(appUrl);
        exec = executionRepo.save(exec);
        runExecutionAsync(exec.getId());
        return AutomationExecutionResponse.from(exec);
    }

    @Async
    @Transactional
    public void runExecutionAsync(Long execId) {
        AutomationExecution exec = executionRepo.findById(execId).orElseThrow();
        try {
            List<Map<String, Object>> rawResults = aiClient.executeTests(
                    exec.getGeneratedCode(), exec.getFrameworkType().name().toLowerCase(),
                    exec.getAppUrl(), exec.getSuiteName());

            int passed = 0, failed = 0, skipped = 0;
            for (Map<String, Object> r : rawResults) {
                AutomationResult result = new AutomationResult();
                result.setExecutionId(execId);
                result.setTestName((String) r.getOrDefault("test_name", "unknown"));
                result.setTestClass((String) r.get("test_class"));
                result.setStatus((String) r.getOrDefault("status", "ERROR"));
                Object dur = r.get("duration_ms");
                if (dur instanceof Number n) result.setDurationMs(n.intValue());
                result.setErrorMessage((String) r.get("error_message"));
                result.setStackTrace((String) r.get("stack_trace"));
                result.setScreenshotBase64((String) r.get("screenshot_base64"));

                if ("FAILED".equals(result.getStatus()) || "ERROR".equals(result.getStatus())) {
                    failed++;
                    String explanation = aiClient.explainFailure(result.getTestName(), result.getErrorMessage());
                    result.setAiExplanation(explanation);
                } else if ("SKIPPED".equals(result.getStatus())) {
                    skipped++;
                } else {
                    passed++;
                }
                resultRepo.save(result);

                // Stream each result via WebSocket
                ws.convertAndSend("/topic/execution/" + exec.getProjectId() + "/results",
                        Map.of("executionId", execId, "result", r));
            }

            exec.setPassed(passed);
            exec.setFailed(failed);
            exec.setSkipped(skipped);
            exec.setTotalTests(rawResults.size());
            exec.setCompletedAt(OffsetDateTime.now());
            exec.setStatus(failed > 0 ? AutomationStatus.FAILED : AutomationStatus.PASSED);
            if (exec.getStartedAt() != null) {
                exec.setDurationMs(exec.getCompletedAt().toInstant().toEpochMilli()
                        - exec.getStartedAt().toInstant().toEpochMilli());
            }
            executionRepo.save(exec);

            if (failed == 0) {
                generateReport(exec);
            }
        } catch (Exception e) {
            log.error("Execution {} failed: {}", execId, e.getMessage());
            exec.setStatus(AutomationStatus.ERROR);
            exec.setCompletedAt(OffsetDateTime.now());
            executionRepo.save(exec);
        }
        ws.convertAndSend("/topic/execution/" + exec.getProjectId(),
                AutomationExecutionResponse.from(executionRepo.findById(execId).orElseThrow()));
    }

    // ─── Report Generation ────────────────────────────────────────────────────

    private void generateReport(AutomationExecution exec) {
        List<AutomationResult> results = resultRepo.findByExecutionIdOrderByCreatedAtAsc(exec.getId());
        String html = buildReportHtml(exec, results);

        GeneratedReport report = new GeneratedReport();
        report.setExecutionId(exec.getId());
        report.setProjectId(exec.getProjectId());
        report.setTitle("QA Report — " + exec.getSuiteName() + " — " + OffsetDateTime.now().toLocalDate());
        report.setHtmlContent(html);
        report.setTotalTests(exec.getTotalTests());
        report.setPassed(exec.getPassed());
        report.setFailed(exec.getFailed());
        report.setExecutionDate(exec.getCompletedAt());
        report.setShareToken(UUID.randomUUID().toString().replace("-", ""));
        if (exec.getTotalTests() > 0) {
            report.setPassRate(BigDecimal.valueOf(exec.getPassed() * 100.0 / exec.getTotalTests())
                    .setScale(2, RoundingMode.HALF_UP));
        }
        reportRepo.save(report);

        exec.setReportUrl("/api/automation/reports/" + report.getShareToken());
        executionRepo.save(exec);
    }

    private String buildReportHtml(AutomationExecution exec, List<AutomationResult> results) {
        StringBuilder sb = new StringBuilder();
        sb.append("""
                <!DOCTYPE html>
                <html lang="en">
                <head><meta charset="UTF-8">
                <title>QA Intelligent Platform — Execution Report</title>
                <style>
                  body{font-family:Inter,sans-serif;margin:0;padding:24px;background:#f8fafc;color:#1e293b}
                  h1{font-size:1.5rem;font-weight:700;margin-bottom:4px}
                  .meta{font-size:.85rem;color:#64748b;margin-bottom:24px}
                  .cards{display:flex;gap:16px;margin-bottom:24px}
                  .card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;flex:1;text-align:center}
                  .card .num{font-size:2rem;font-weight:800}
                  .pass{color:#16a34a}.fail{color:#dc2626}.skip{color:#6b7280}
                  table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0}
                  th{background:#f1f5f9;padding:12px;text-align:left;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:#64748b}
                  td{padding:12px;border-top:1px solid #f1f5f9;font-size:.85rem}
                  .badge{display:inline-flex;padding:2px 8px;border-radius:9999px;font-size:.7rem;font-weight:600}
                  .badge-pass{background:#dcfce7;color:#16a34a}
                  .badge-fail{background:#fee2e2;color:#dc2626}
                  .badge-skip{background:#f1f5f9;color:#6b7280}
                </style>
                </head>
                <body>
                """);
        sb.append("<h1>QA Intelligent Platform — Execution Report</h1>");
        sb.append("<div class='meta'>Suite: ").append(exec.getSuiteName())
          .append(" &nbsp;|&nbsp; Framework: ").append(exec.getFrameworkType())
          .append(" &nbsp;|&nbsp; Date: ").append(exec.getCompletedAt())
          .append("</div>");
        sb.append("<div class='cards'>");
        sb.append("<div class='card'><div class='num'>").append(exec.getTotalTests()).append("</div><div>Total</div></div>");
        sb.append("<div class='card'><div class='num pass'>").append(exec.getPassed()).append("</div><div>Passed</div></div>");
        sb.append("<div class='card'><div class='num fail'>").append(exec.getFailed()).append("</div><div>Failed</div></div>");
        int pct = exec.getTotalTests() > 0 ? (int) (exec.getPassed() * 100.0 / exec.getTotalTests()) : 0;
        sb.append("<div class='card'><div class='num ").append(pct >= 80 ? "pass" : "fail").append("'>").append(pct).append("%</div><div>Pass Rate</div></div>");
        sb.append("</div>");
        sb.append("<table><thead><tr><th>Test</th><th>Status</th><th>Duration</th><th>Error</th></tr></thead><tbody>");
        for (AutomationResult r : results) {
            String badge = "PASSED".equals(r.getStatus()) ? "badge-pass" : "SKIPPED".equals(r.getStatus()) ? "badge-skip" : "badge-fail";
            sb.append("<tr><td>").append(r.getTestName()).append("</td>")
              .append("<td><span class='badge ").append(badge).append("'>").append(r.getStatus()).append("</span></td>")
              .append("<td>").append(r.getDurationMs() != null ? r.getDurationMs() + "ms" : "—").append("</td>")
              .append("<td>").append(r.getErrorMessage() != null ? r.getErrorMessage() : "").append("</td></tr>");
        }
        sb.append("</tbody></table></body></html>");
        return sb.toString();
    }

    // ─── Queries ─────────────────────────────────────────────────────────────

    public List<AutomationExecutionResponse> getExecutions(Long projectId) {
        return executionRepo.findByProjectIdOrderByCreatedAtDesc(projectId).stream()
                .map(AutomationExecutionResponse::from).toList();
    }

    public AutomationExecutionResponse getExecution(Long id) {
        return executionRepo.findById(id).map(AutomationExecutionResponse::from)
                .orElseThrow(() -> new RuntimeException("Execution not found"));
    }

    public List<Map<String, Object>> getResults(Long executionId) {
        return resultRepo.findByExecutionIdOrderByCreatedAtAsc(executionId).stream()
                .map(r -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", r.getId());
                    m.put("testName", r.getTestName());
                    m.put("testClass", r.getTestClass());
                    m.put("status", r.getStatus());
                    m.put("durationMs", r.getDurationMs());
                    m.put("errorMessage", r.getErrorMessage());
                    m.put("screenshotBase64", r.getScreenshotBase64());
                    m.put("aiExplanation", r.getAiExplanation());
                    m.put("jiraTicketKey", r.getJiraTicketKey());
                    m.put("jiraTicketUrl", r.getJiraTicketUrl());
                    return m;
                }).toList();
    }

    public Optional<GeneratedReport> getReportByToken(String token) {
        return reportRepo.findByShareToken(token);
    }

    public List<Map<String, Object>> getReports(Long projectId) {
        return reportRepo.findByProjectIdOrderByCreatedAtDesc(projectId).stream()
                .map(r -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("id", r.getId());
                    m.put("title", r.getTitle());
                    m.put("passRate", r.getPassRate());
                    m.put("totalTests", r.getTotalTests());
                    m.put("passed", r.getPassed());
                    m.put("failed", r.getFailed());
                    m.put("shareToken", r.getShareToken());
                    m.put("executionDate", r.getExecutionDate());
                    m.put("createdAt", r.getCreatedAt());
                    return m;
                }).toList();
    }

    private String toJson(Object o) {
        if (o == null) return null;
        if (o instanceof String s) return s;
        try { return mapper.writeValueAsString(o); } catch (Exception e) { return o.toString(); }
    }

    // ─── Framework File Explorer ──────────────────────────────────────────────

    public List<Map<String, Object>> getFileTree(Long profileId) {
        FrameworkProfile fp = frameworkRepo.findById(profileId).orElseThrow();
        String[] ownerRepo = parseGitHubUrl(fp.getRepoUrl());
        List<Map<String, Object>> result = new ArrayList<>();
        for (String testDir : List.of("test", "tests")) {
            try {
                List<Map<String, Object>> entries = githubListDir(ownerRepo, testDir, fp.getBranch(), fp.getGithubToken());
                for (Map<String, Object> e : entries) {
                    Map<String, Object> node = new LinkedHashMap<>(e);
                    result.add(node);
                    if ("dir".equals(e.get("type"))) {
                        try {
                            List<Map<String, Object>> children = githubListDir(ownerRepo, (String) e.get("path"), fp.getBranch(), fp.getGithubToken());
                            children.forEach(c -> { Map<String, Object> child = new LinkedHashMap<>(c); child.put("parent", e.get("name")); result.add(child); });
                        } catch (Exception ignored) {}
                    }
                }
                break;
            } catch (Exception ignored) {}
        }
        return result;
    }

    public Map<String, Object> getFileContent(Long profileId, String path) {
        FrameworkProfile fp = frameworkRepo.findById(profileId).orElseThrow();
        String[] ownerRepo = parseGitHubUrl(fp.getRepoUrl());
        try {
            String url = "https://api.github.com/repos/" + ownerRepo[0] + "/" + ownerRepo[1]
                    + "/contents/" + path + "?ref=" + fp.getBranch();
            HttpRequest.Builder rb = HttpRequest.newBuilder().uri(URI.create(url))
                    .header("Accept", "application/vnd.github+json").header("X-GitHub-Api-Version", "2022-11-28");
            if (fp.getGithubToken() != null) rb.header("Authorization", "Bearer " + fp.getGithubToken());
            HttpResponse<String> resp = http.send(rb.GET().build(), HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() >= 400) throw new RuntimeException("GitHub error " + resp.statusCode());
            @SuppressWarnings("unchecked") Map<String, Object> data = mapper.readValue(resp.body(), Map.class);
            String b64 = ((String) data.get("content")).replaceAll("\\s", "");
            String content = new String(Base64.getDecoder().decode(b64), StandardCharsets.UTF_8);
            return Map.of("path", path, "content", content, "sha", data.getOrDefault("sha", ""));
        } catch (Exception e) { throw new RuntimeException("Cannot fetch file: " + e.getMessage()); }
    }

    public Map<String, Object> saveFileContent(Long profileId, String path, String content, String sha, String commitMessage) {
        FrameworkProfile fp = frameworkRepo.findById(profileId).orElseThrow();
        String[] ownerRepo = parseGitHubUrl(fp.getRepoUrl());
        try {
            String url = "https://api.github.com/repos/" + ownerRepo[0] + "/" + ownerRepo[1] + "/contents/" + path;
            String b64 = Base64.getEncoder().encodeToString(content.getBytes(StandardCharsets.UTF_8));
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("message", commitMessage != null ? commitMessage : "feat: update tests via QAIP");
            body.put("content", b64);
            body.put("branch", fp.getBranch());
            if (sha != null && !sha.isBlank()) body.put("sha", sha);
            String bodyJson = mapper.writeValueAsString(body);
            HttpRequest.Builder rb = HttpRequest.newBuilder().uri(URI.create(url))
                    .header("Accept", "application/vnd.github+json")
                    .header("Content-Type", "application/json")
                    .header("X-GitHub-Api-Version", "2022-11-28");
            if (fp.getGithubToken() != null) rb.header("Authorization", "Bearer " + fp.getGithubToken());
            HttpResponse<String> resp = http.send(rb.PUT(HttpRequest.BodyPublishers.ofString(bodyJson)).build(), HttpResponse.BodyHandlers.ofString());
            if (resp.statusCode() >= 400) throw new RuntimeException("GitHub save error " + resp.statusCode() + ": " + resp.body());
            @SuppressWarnings("unchecked") Map<String, Object> result = mapper.readValue(resp.body(), Map.class);
            @SuppressWarnings("unchecked") Map<String, Object> contentObj = (Map<String, Object>) result.get("content");
            return Map.of("committed", true, "sha", contentObj != null ? contentObj.getOrDefault("sha", "") : "", "message", commitMessage != null ? commitMessage : "");
        } catch (Exception e) { throw new RuntimeException("Cannot save file: " + e.getMessage()); }
    }

    public AutomationExecutionResponse executeFromFramework(Long profileId, List<String> testNames, boolean allTests) {
        FrameworkProfile fp = frameworkRepo.findById(profileId).orElseThrow();
        List<String> titles = allTests ? resolveAllTestTitles(profileId) : testNames;
        GenerateAutomationRequest req = new GenerateAutomationRequest();
        req.setProjectId(fp.getProjectId());
        req.setFrameworkProfileId(profileId);
        req.setSuiteName(allTests ? "Execute All — " + fp.getRepoUrl().replaceAll(".*/", "") : "Execute New — " + titles.size() + " tests");
        req.setTestCaseTitles(titles);
        AutomationExecutionResponse exec = generateAutomationCode(req);
        return startExecution(exec.getId(), null);
    }

    private List<String> resolveAllTestTitles(Long profileId) {
        try {
            List<Map<String, Object>> tree = getFileTree(profileId);
            List<String> titles = new ArrayList<>();
            Pattern p = Pattern.compile("test\\s*\\(\\s*['\"`](.+?)['\"`]");
            for (Map<String, Object> node : tree) {
                String name = (String) node.get("name");
                String type = (String) node.get("type");
                if ("file".equals(type) && name != null && name.endsWith(".spec.ts")) {
                    try {
                        Map<String, Object> fc = getFileContent(profileId, (String) node.get("path"));
                        Matcher m = p.matcher((String) fc.get("content"));
                        while (m.find()) titles.add(m.group(1));
                    } catch (Exception ignored) {}
                }
            }
            return titles.isEmpty() ? List.of("All tests") : titles;
        } catch (Exception e) { return List.of("All tests"); }
    }

    private String[] parseGitHubUrl(String repoUrl) {
        String path = repoUrl.replaceFirst("https?://github\\.com/", "").replaceAll("\\.git$", "").replaceAll("/$", "");
        String[] parts = path.split("/", 2);
        return parts.length == 2 ? parts : new String[]{"unknown", "unknown"};
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> githubListDir(String[] ownerRepo, String dirPath, String branch, String token) throws Exception {
        String url = "https://api.github.com/repos/" + ownerRepo[0] + "/" + ownerRepo[1]
                + "/contents/" + dirPath + "?ref=" + branch;
        HttpRequest.Builder rb = HttpRequest.newBuilder().uri(URI.create(url))
                .header("Accept", "application/vnd.github+json").header("X-GitHub-Api-Version", "2022-11-28");
        if (token != null && !token.isBlank()) rb.header("Authorization", "Bearer " + token);
        HttpResponse<String> resp = http.send(rb.GET().build(), HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() >= 400) throw new RuntimeException("GitHub error " + resp.statusCode());
        List<Map<String, Object>> raw = mapper.readValue(resp.body(), List.class);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> f : raw) {
            Map<String, Object> node = new LinkedHashMap<>();
            node.put("name", f.get("name"));
            node.put("path", f.get("path"));
            node.put("type", "dir".equals(f.get("type")) ? "dir" : "file");
            node.put("sha", f.getOrDefault("sha", ""));
            result.add(node);
        }
        return result;
    }
}

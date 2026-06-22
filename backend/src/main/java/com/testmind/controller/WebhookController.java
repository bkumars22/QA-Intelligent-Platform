package com.testmind.controller;

import com.testmind.repository.ProjectRepository;
import com.testmind.service.AiEngineClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/webhook")
public class WebhookController {

    private static final Logger log = LoggerFactory.getLogger(WebhookController.class);

    private final ProjectRepository projectRepo;
    private final AiEngineClient aiClient;

    public WebhookController(ProjectRepository projectRepo, AiEngineClient aiClient) {
        this.projectRepo = projectRepo;
        this.aiClient = aiClient;
    }

    /**
     * GitHub push webhook.
     * Register at: https://github.com/bkumars22/SupplyChainPlatformProject/settings/hooks
     * Register at: https://github.com/bkumars22/ARIA/settings/hooks
     * Payload URL: https://testmind-production.up.railway.app/api/webhook/github
     * Content type: application/json
     * Events: Just the push event
     */
    @PostMapping("/github")
    public ResponseEntity<Map<String, Object>> handleGithubPush(
            @RequestHeader(value = "X-GitHub-Event", defaultValue = "push") String event,
            @RequestBody Map<String, Object> payload) {

        if (!"push".equals(event)) {
            return ResponseEntity.ok(Map.of("status", "ignored", "event", event));
        }

        String repoFullName = extractRepoFullName(payload);
        String commitSha = extractCommitSha(payload);
        String branch = extractBranch(payload);

        if (repoFullName == null || commitSha == null) {
            return ResponseEntity.ok(Map.of("status", "skipped", "reason", "missing repo or sha"));
        }

        // Only trigger on main/master branch
        if (branch != null && !branch.equals("main") && !branch.equals("master")) {
            return ResponseEntity.ok(Map.of("status", "skipped", "reason", "not main branch: " + branch));
        }

        String repoUrl = "https://github.com/" + repoFullName;
        log.info("GitHub push webhook: repo={} sha={}", repoFullName, commitSha);

        // Find the matching project and trigger analysis
        projectRepo.findAll().stream()
                .filter(p -> repoUrl.equalsIgnoreCase(p.getRepoUrl())
                        || repoFullName.equalsIgnoreCase(extractOwnerRepo(p.getRepoUrl())))
                .findFirst()
                .ifPresentOrElse(
                        project -> {
                            log.info("Triggering analysis for project {} on push to {}", project.getId(), repoUrl);
                            aiClient.triggerAnalysis(project.getId(), repoUrl,
                                    project.getGithubToken(), commitSha);
                        },
                        () -> log.warn("No project found for repo: {}", repoUrl)
                );

        return ResponseEntity.ok(Map.of("status", "accepted", "repo", repoFullName, "sha", commitSha));
    }

    @SuppressWarnings("unchecked")
    private String extractRepoFullName(Map<String, Object> payload) {
        try {
            Map<String, Object> repo = (Map<String, Object>) payload.get("repository");
            return repo != null ? (String) repo.get("full_name") : null;
        } catch (Exception e) { return null; }
    }

    private String extractCommitSha(Map<String, Object> payload) {
        Object sha = payload.get("after");
        return sha instanceof String s ? s : null;
    }

    private String extractBranch(Map<String, Object> payload) {
        Object ref = payload.get("ref");
        if (ref instanceof String r) {
            return r.replace("refs/heads/", "");
        }
        return null;
    }

    private String extractOwnerRepo(String repoUrl) {
        if (repoUrl == null) return "";
        return repoUrl.replace("https://github.com/", "").replace(".git", "");
    }
}

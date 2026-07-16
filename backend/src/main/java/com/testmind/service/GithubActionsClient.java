package com.testmind.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Dispatches performance.yml via GitHub's Actions API and polls for the
 * resulting run. workflow_dispatch doesn't return a run id, so the caller
 * records the dispatch timestamp and this client finds the matching run by
 * querying runs created after that timestamp -- GitHub's own documented
 * workaround for this API gap.
 */
@Service
@Slf4j
public class GithubActionsClient {

    @Value("${github.actions.token:}")
    private String token;

    @Value("${github.actions.repo:bkumars22/QA-Intelligent-Platform}")
    private String repo;

    private static final String WORKFLOW_FILE = "performance.yml";

    public boolean isConfigured() {
        return token != null && !token.isBlank();
    }

    private WebClient webClient() {
        return WebClient.builder()
                .baseUrl("https://api.github.com")
                .defaultHeader("Authorization", "Bearer " + token)
                .defaultHeader("Accept", "application/vnd.github+json")
                .defaultHeader("X-GitHub-Api-Version", "2022-11-28")
                .build();
    }

    public void dispatchWorkflow(String system, String host, int users, String runTime) {
        Map<String, Object> body = Map.of(
                "ref", "main",
                "inputs", Map.of(
                        "system", system,
                        "host", host,
                        "users", String.valueOf(users),
                        "run_time", runTime
                )
        );

        webClient()
                .post()
                .uri("/repos/{repo}/actions/workflows/{workflow}/dispatches", repo, WORKFLOW_FILE)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(body)
                .retrieve()
                .toBodilessEntity()
                .block();

        log.info("Dispatched {} workflow for system={} host={}", WORKFLOW_FILE, system, host);
    }

    @SuppressWarnings("unchecked")
    public Optional<Map<String, Object>> findRunDispatchedAfter(OffsetDateTime dispatchedAt) {
        String created = "%3E" + dispatchedAt.minusSeconds(5).toString(); // URL-encoded ">"

        Map<String, Object> response = webClient()
                .get()
                .uri("/repos/{repo}/actions/workflows/{workflow}/runs?created={created}&event=workflow_dispatch",
                        repo, WORKFLOW_FILE, created)
                .retrieve()
                .bodyToMono(Map.class)
                .block();

        if (response == null) return Optional.empty();
        List<Map<String, Object>> runs = (List<Map<String, Object>>) response.get("workflow_runs");
        if (runs == null || runs.isEmpty()) return Optional.empty();

        // Runs are returned newest-first -- the most recent one after our dispatch timestamp is ours.
        return Optional.of(runs.get(runs.size() - 1));
    }
}

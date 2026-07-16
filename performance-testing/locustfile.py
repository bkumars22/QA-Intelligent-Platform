"""
QAIP Performance Test — Locust load test definitions.

Why Locust over k6/JMeter: it's Python-native, so it plugs directly into
the same stack as the rest of QAIP's AI engine (same language your team
already reads and maintains), and its results parse cleanly into the
metrics_analyzer.py module below.

Endpoints below are QAIP's real backend routes (see backend/src/main/java/
com/testmind/controller/) — not placeholders. A project must already exist
for the login user for get_risk_score/get_dashboard/list_automation_executions/
trigger_ai_analysis to have something to act on; on_start looks up the first
project on the account rather than assuming a fixed ID.

Run locally:
    locust -f locustfile.py --host http://localhost:8080

Run headless (for CI):
    locust -f locustfile.py --host http://localhost:8080 \
        --headless --users 200 --spawn-rate 10 --run-time 5m \
        --csv=results/perf_run
"""

from locust import HttpUser, task, between, events


@events.init_command_line_parser.add_listener
def _add_custom_args(parser):
    parser.add_argument("--test-email", type=str, default="loadtest@qaip.internal",
                         help="Login email for simulated users (must already exist)")
    parser.add_argument("--test-password", type=str, default="loadtest-password",
                         help="Login password for simulated users")


class QAIPAPIUser(HttpUser):
    """
    Simulates realistic traffic patterns — not just hammering one endpoint.
    Weighted tasks reflect actual usage: risk-score lookups happen far
    more often than triggering a full AI analysis run.
    """
    wait_time = between(1, 3)  # simulates real user think-time between actions

    def on_start(self):
        """Runs once per simulated user — authenticate, then grab a real project ID."""
        response = self.client.post("/api/auth/login", json={
            "email": self.environment.parsed_options.test_email,
            "password": self.environment.parsed_options.test_password,
        })
        # AuthResponse (backend/src/main/java/com/testmind/dto/AuthResponse.java)
        # returns "accessToken", not "token".
        self.token = response.json().get("accessToken", "")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        projects = self.client.get("/api/projects", headers=self.headers).json()
        self.project_id = projects[0]["id"] if projects else None

    @task(10)
    def get_risk_score(self):
        """Most common operation — checking a project's risk scores. Weight: 10."""
        if not self.project_id:
            return
        self.client.get(
            f"/api/projects/{self.project_id}/risk-scores",
            headers=self.headers,
            name="/api/projects/[id]/risk-scores",  # groups all variants under one metric bucket
        )

    @task(5)
    def get_dashboard(self):
        """Dashboard load — moderate frequency. Weight: 5."""
        self.client.get("/api/dashboard/stats", headers=self.headers)

    @task(2)
    def list_automation_executions(self):
        """Browsing recent test runs. Weight: 2."""
        if not self.project_id:
            return
        self.client.get(
            f"/api/automation/projects/{self.project_id}/executions",
            headers=self.headers,
            name="/api/automation/projects/[id]/executions",
        )

    @task(1)
    def trigger_ai_analysis(self):
        """
        Least frequent but heaviest operation — triggers a full AI analysis
        run for a project (backend/.../ProjectController.runAnalysis ->
        AiEngineClient.triggerAnalysis -> ai-engine's /analyze). Returns 202
        immediately with a runId; the actual pipeline runs async.
        """
        if not self.project_id:
            return
        self.client.post(
            f"/api/projects/{self.project_id}/run-analysis",
            headers=self.headers,
            name="/api/projects/[id]/run-analysis",
        )

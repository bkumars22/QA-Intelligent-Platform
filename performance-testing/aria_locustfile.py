"""
ARIA Performance Test — traffic for the adaptive learning platform.

Endpoints verified against ARIA's real backend (com.aria.agent.SessionController,
com.aria.progress.ProgressController, com.aria.homework.HomeworkController) and
its Python AI service's TeachRequest model — not guessed. Unlike QAIP, ARIA's
core interaction is stateful: you must create a session before you can chat in
it, and the chat body must satisfy TeachRequest's required fields
(student_id, student_name, grade, student_input).

Run locally:
    locust -f aria_locustfile.py --host http://localhost:8080
"""

from locust import HttpUser, task, between, events
import random

GRADES = list(range(1, 13))
SUBJECTS = ["Mathematics", "Science", "English"]


@events.init_command_line_parser.add_listener
def _add_custom_args(parser):
    parser.add_argument("--test-student-id", type=str, default="1",
                         help="student_id to use for simulated sessions (must already exist)")


class ARIAUser(HttpUser):
    """
    No login wall on the endpoints exercised here — ARIA's session/chat/
    progress/homework routes don't require auth in the current backend.
    """
    wait_time = between(2, 6)  # students think/type slower than API clients

    def on_start(self):
        """Create one real learning session per simulated user, like a real student would."""
        student_id = self.environment.parsed_options.test_student_id
        resp = self.client.post("/api/sessions", json={
            "studentId": student_id,
            "subject": random.choice(SUBJECTS),
        })
        data = resp.json().get("data", {}) if resp.ok else {}
        self.session_id = data.get("id")
        self.student_id = student_id

    @task(10)
    def chat(self):
        """Core Socratic-tutoring flow — highest volume by far."""
        if not self.session_id:
            return
        self.client.post(
            f"/api/sessions/{self.session_id}/chat",
            json={
                "student_id": str(self.student_id),
                "student_name": "Load Test Student",
                "grade": random.choice(GRADES),
                "language": "en",
                "student_input": "What is 7 times 8?",
            },
            name="/api/sessions/[id]/chat",
        )

    @task(4)
    def check_progress(self):
        self.client.get(
            f"/api/progress/student/{self.student_id}",
            name="/api/progress/student/[id]",
        )

    @task(1)
    def homework_solve(self):
        """
        Heaviest, least frequent operation — multipart request, no real
        file attached (keeps the load test itself lightweight while still
        exercising the endpoint's non-file code path).
        """
        self.client.post(
            "/api/homework/solve",
            data={
                "studentQuestion": "How do I solve for x in 2x + 3 = 11?",
                "grade": str(random.choice(GRADES)),
                "language": "en",
                "studentLevel": "AVERAGE",
                "wantFullAnswer": "true",
                "wantStepByStep": "true",
                "studentId": str(self.student_id),
            },
            name="/api/homework/solve",
        )

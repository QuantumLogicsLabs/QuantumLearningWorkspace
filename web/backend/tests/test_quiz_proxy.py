import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient

from main import app
from auth_utils import create_access_token
from database import get_quiz_sessions_collection, get_quiz_results_collection


class TestQuizProxyAndGrading(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_patcher = patch("database.get_client", return_value=None)
        self.db_patcher.start()
        self.client = TestClient(app)
        self.test_email = "tester@example.com"
        self.token = create_access_token(self.test_email)
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db_patcher.stop()

    @patch("httpx.AsyncClient.post")
    async def test_generate_quiz_proxies_and_strips_answers(self, mock_post):
        mock_post.return_value = httpx.Response(
            200,
            json={
                "success": True,
                "message": "Generated 2 questions.",
                "questions": [
                    {
                        "question_id": "q-1",
                        "question": "What is photosynthesis?",
                        "question_type": "mcq",
                        "options": ["A", "B", "C", "D"],
                        "difficulty": "medium",
                        "topic": "Biology",
                    },
                    {
                        "question_id": "q-2",
                        "question": "Is the Earth round?",
                        "question_type": "true_false",
                        "options": ["True", "False"],
                        "difficulty": "easy",
                        "topic": "Geography",
                    },
                ],
                "answers": [
                    {
                        "question_id": "q-1",
                        "answer": "B",
                        "explanation": "Plants use light to make energy.",
                    },
                    {
                        "question_id": "q-2",
                        "answer": "True",
                        "explanation": "The Earth is an oblate spheroid.",
                    },
                ],
            },
        )

        response = self.client.post(
            "/generate-quiz",
            json={
                "topic": "Biology",
                "question_count": 2,
                "quiz_type": "mcq",
            },
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["success"])
        self.assertIn("quiz_id", data)
        self.assertEqual(len(data["questions"]), 2)

        # SECURITY: Answers MUST NEVER be in the response
        self.assertNotIn("answers", data)
        for q in data["questions"]:
            self.assertNotIn("answer", q)
            self.assertNotIn("correct_answer", q)
            self.assertNotIn("explanation", q)
            self.assertIn("question_id", q)
            self.assertIn("question", q)

        quiz_sessions = get_quiz_sessions_collection()
        session = await quiz_sessions.find_one({"quiz_id": data["quiz_id"]})
        self.assertIsNotNone(session)
        assert session is not None
        self.assertEqual(len(session["answers"]), 2)
        self.assertEqual(session["answers"][0]["answer"], "B")

    @patch("httpx.AsyncClient.post")
    async def test_server_side_grading_full_flow(self, mock_post):
        mock_post.return_value = httpx.Response(
            200,
            json={
                "success": True,
                "message": "Generated 2 questions.",
                "questions": [
                    {
                        "question_id": "q-101",
                        "question": "What is H2O?",
                        "question_type": "mcq",
                        "options": ["Water", "Oxygen", "Hydrogen", "Carbon"],
                        "difficulty": "easy",
                        "topic": "Chemistry",
                    },
                    {
                        "question_id": "q-102",
                        "question": "The speed of light is 300,000 km/s.",
                        "question_type": "true_false",
                        "options": ["True", "False"],
                        "difficulty": "medium",
                        "topic": "Physics",
                    },
                ],
                "answers": [
                    {
                        "question_id": "q-101",
                        "answer": "Water",
                        "explanation": "H2O is water.",
                    },
                    {
                        "question_id": "q-102",
                        "answer": "True",
                        "explanation": "Light travels at approx 300,000 km/s.",
                    },
                ],
            },
        )

        gen_resp = self.client.post(
            "/generate-quiz",
            json={
                "topic": "Science",
                "question_count": 2,
                "quiz_type": "mcq",
            },
            headers=self.auth_headers,
        )
        self.assertEqual(gen_resp.status_code, 200)
        quiz_id = gen_resp.json()["quiz_id"]

        # Submit answers: 1 Correct, 1 Incorrect
        sub_resp = self.client.post(
            "/submit-quiz",
            json={
                "quiz_id": quiz_id,
                "topic": "Science",
                "answers": {
                    "q-101": "  water  ",
                    "q-102": "False",
                },
            },
            headers=self.auth_headers,
        )

        self.assertEqual(sub_resp.status_code, 200)
        grade_data = sub_resp.json()
        self.assertTrue(grade_data["success"])
        self.assertEqual(grade_data["score"], 1)
        self.assertEqual(grade_data["total"], 2)
        self.assertEqual(grade_data["percentage"], 50)

        results_map = {r["question_id"]: r for r in grade_data["results"]}
        self.assertTrue(results_map["q-101"]["is_correct"])
        self.assertEqual(results_map["q-101"]["correct_answer"], "Water")
        self.assertEqual(results_map["q-101"]["explanation"], "H2O is water.")
        self.assertFalse(results_map["q-102"]["is_correct"])
        self.assertEqual(results_map["q-102"]["correct_answer"], "True")

        get_res_resp = self.client.get("/quiz-results", headers=self.auth_headers)
        self.assertEqual(get_res_resp.status_code, 200)
        res_list = get_res_resp.json()
        saved_qids = [r["question_id"] for r in res_list]
        self.assertIn("q-101", saved_qids)
        self.assertIn("q-102", saved_qids)

    @patch("httpx.AsyncClient.post")
    async def test_grading_with_list_format_and_fallback_matching(self, mock_post):
        mock_post.return_value = httpx.Response(
            200,
            json={
                "success": True,
                "questions": [
                    {
                        "question_id": "q-201",
                        "question": "Fill in the blank: The powerhouse of the cell is the ___.",
                        "question_type": "fill_blank",
                    }
                ],
                "answers": [
                    {
                        "question_id": "q-201",
                        "answer": "mitochondria",
                        "explanation": "Mitochondria generates ATP.",
                    }
                ],
            },
        )

        gen_resp = self.client.post(
            "/generate-quiz",
            json={"topic": "Cell Biology", "question_count": 1, "quiz_type": "fill_blank"},
            headers=self.auth_headers,
        )
        self.assertEqual(gen_resp.status_code, 200)

        # Submit as list of answers without quiz_id (tests fallback matching)
        sub_resp = self.client.post(
            "/submit-quiz",
            json={
                "topic": "Cell Biology",
                "answers": [
                    {"question_id": "q-201", "selected_answer": "Mitochondria"}
                ],
            },
            headers=self.auth_headers,
        )
        self.assertEqual(sub_resp.status_code, 200)
        grade_data = sub_resp.json()
        self.assertEqual(grade_data["score"], 1)
        self.assertEqual(grade_data["percentage"], 100)
        self.assertTrue(grade_data["results"][0]["is_correct"])

    def test_submit_quiz_empty_answers_error(self):
        resp = self.client.post(
            "/submit-quiz",
            json={"quiz_id": "some-id", "answers": {}},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 400)

    def test_submit_quiz_nonexistent_session_error(self):
        resp = self.client.post(
            "/submit-quiz",
            json={"quiz_id": "nonexistent-id", "answers": {"q-unknown": "test"}},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 404)

    def test_submit_quiz_requires_auth(self):
        resp = self.client.post(
            "/submit-quiz",
            json={"quiz_id": "test", "answers": {"q-1": "A"}},
        )
        self.assertEqual(resp.status_code, 401)

    @patch("httpx.AsyncClient.post")
    def test_upstream_connection_error(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        resp = self.client.post(
            "/generate-quiz",
            json={"topic": "Math", "quiz_type": "mcq", "question_count": 5},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Quiz generator service is unavailable", resp.json()["detail"])

    @patch("httpx.AsyncClient.post")
    def test_upstream_timeout_error(self, mock_post):
        mock_post.side_effect = httpx.ReadTimeout("Read timed out")
        resp = self.client.post(
            "/generate-quiz",
            json={"topic": "Math", "quiz_type": "mcq", "question_count": 5},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 504)
        self.assertIn("took too long to respond", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()

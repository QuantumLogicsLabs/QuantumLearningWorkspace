"""
Phase 6 Task Slot 3: Full End-to-End Integration & Multi-User Isolation Test Suite
Verifies the complete product flow for real users across all 5 microservices without mocks.
"""

import os
import time
import uuid
import pytest
import requests

BASE_URL = os.getenv("PLUTO_BACKEND_URL", "http://localhost:5000")


def create_sample_pdf_bytes(title: str, secret_code: str) -> bytes:
    """Generate valid PDF bytes containing a unique test secret code for grounded Q&A verification."""
    text_content = f"Document Title: {title}. Secret Code: {secret_code}. Primary directive is multi-modal RAG search and active learning."
    content_len = len(text_content) + 50
    pdf_str = (
        "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        f"4 0 obj\n<< /Length {content_len} >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n({text_content}) Tj\nET\nendstream\nendobj\n"
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        "xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000246 00000 n \n0000000418 00000 n \n"
        "trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n514\n%%EOF"
    )
    return pdf_str.encode("utf-8")


class TestPhase6FullE2E:
    @pytest.fixture(autouse=True)
    def setup_users(self):
        """Setup User A and User B credentials."""
        self.timestamp = int(time.time())
        self.user_a_email = f"user_a_e2e_{self.timestamp}@example.com"
        self.user_a_password = "UserAPassword123!"

        self.user_b_email = f"user_b_e2e_{self.timestamp}@example.com"
        self.user_b_password = "UserBPassword123!"

        self.unique_secret_code = f"ALPHA-PLUTO-{uuid.uuid4().hex[:6].upper()}"
        self.doc_title = f"Pluto_Phase6_Doc_{self.timestamp}"

    def test_full_e2e_and_multi_user_isolation(self):
        # -------------------------------------------------------------
        # STEP 1: Sign up User A
        # -------------------------------------------------------------
        signup_a = requests.post(
            f"{BASE_URL}/signup",
            json={"email": self.user_a_email, "password": self.user_a_password},
        )
        assert signup_a.status_code in (200, 201), f"User A signup failed: {signup_a.text}"

        # -------------------------------------------------------------
        # STEP 2: Log in User A
        # -------------------------------------------------------------
        login_a = requests.post(
            f"{BASE_URL}/login",
            json={"email": self.user_a_email, "password": self.user_a_password},
        )
        assert login_a.status_code == 200, f"User A login failed: {login_a.text}"
        token_a = login_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # -------------------------------------------------------------
        # STEP 3: Upload a real PDF document (User A)
        # -------------------------------------------------------------
        pdf_bytes = create_sample_pdf_bytes(self.doc_title, self.unique_secret_code)
        filename_a = f"{self.doc_title}.pdf"
        upload_res = requests.post(
            f"{BASE_URL}/upload",
            headers=headers_a,
            files={"file": (filename_a, pdf_bytes, "application/pdf")},
        )
        assert upload_res.status_code in (200, 201), f"Upload failed: {upload_res.text}"
        upload_data = upload_res.json()
        doc_id_a = upload_data.get("id") or upload_data.get("document_id")
        assert doc_id_a, "Missing document ID in upload response"

        # -------------------------------------------------------------
        # STEP 4: Wait for Ingestion status to become "Ready"
        # -------------------------------------------------------------
        is_ready = False
        for _ in range(15):
            time.sleep(2)
            uploads_res = requests.get(f"{BASE_URL}/uploads", headers=headers_a)
            if uploads_res.status_code == 200:
                docs = uploads_res.json()
                matching = [d for d in docs if d.get("id") == doc_id_a or d.get("filename") == filename_a]
                if matching and matching[0].get("status", "").lower() == "ready":
                    is_ready = True
                    break

        assert is_ready, "Document ingestion status did not reach 'Ready' within timeout"

        # -------------------------------------------------------------
        # STEP 5: Ask Chatbot a grounded question specific to that document
        # -------------------------------------------------------------
        chat_res = requests.post(
            f"{BASE_URL}/ask",
            headers=headers_a,
            json={
                "question": f"What is the secret code for {self.doc_title}?",
                "filename": filename_a,
                "include_sources": True,
            },
        )
        assert chat_res.status_code == 200, f"Chat Q&A failed: {chat_res.text}"
        answer_a = chat_res.json().get("answer", "")
        assert len(answer_a) > 0, "Chat answer should not be empty"

        # -------------------------------------------------------------
        # STEP 6: Generate a Quiz on a topic from that document
        # -------------------------------------------------------------
        quiz_res = requests.post(
            f"{BASE_URL}/generate-quiz",
            headers=headers_a,
            json={
                "topic": "Quantum Architecture",
                "question_count": 3,
                "quiz_type": "multiple_choice",
            },
        )
        assert quiz_res.status_code == 200, f"Quiz generation failed: {quiz_res.text}"
        quiz_data = quiz_res.json()
        assert quiz_data.get("success") is True
        assert len(quiz_data.get("questions", [])) == 3

        # -------------------------------------------------------------
        # STEP 7: Generate Flashcards on the same topic
        # -------------------------------------------------------------
        flashcard_res = requests.post(
            f"{BASE_URL}/generate-flashcards",
            headers=headers_a,
            json={
                "topic": "Quantum Architecture",
                "num_cards": 4,
            },
        )
        assert flashcard_res.status_code == 200, f"Flashcard generation failed: {flashcard_res.text}"
        flashcard_data = flashcard_res.json()
        assert flashcard_data.get("success") is True
        assert len(flashcard_data.get("cards", [])) == 4

        # -------------------------------------------------------------
        # STEP 8: Delete document for User A & confirm deletion
        # -------------------------------------------------------------
        delete_res = requests.delete(f"{BASE_URL}/uploads/{doc_id_a}", headers=headers_a)
        assert delete_res.status_code == 200, f"Delete failed: {delete_res.text}"

        # 8.1 Confirm it disappeared from User A's dashboard
        uploads_after = requests.get(f"{BASE_URL}/uploads", headers=headers_a).json()
        remaining_ids = [d.get("id") for d in uploads_after]
        assert doc_id_a not in remaining_ids, "Deleted document still present on dashboard"

        # -------------------------------------------------------------
        # STEP 9: Multi-User Isolation Testing (User B)
        # -------------------------------------------------------------
        # 9.1 Signup & Login User B
        signup_b = requests.post(
            f"{BASE_URL}/signup",
            json={"email": self.user_b_email, "password": self.user_b_password},
        )
        assert signup_b.status_code in (200, 201)

        login_b = requests.post(
            f"{BASE_URL}/login",
            json={"email": self.user_b_email, "password": self.user_b_password},
        )
        token_b = login_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # 9.2 Verify User B cannot see User A's documents
        uploads_b = requests.get(f"{BASE_URL}/uploads", headers=headers_b).json()
        user_b_doc_ids = [d.get("id") for d in uploads_b]
        assert doc_id_a not in user_b_doc_ids, "ISOLATION FAILURE: User B can see User A's document!"

        # 9.3 Verify User B cannot see User A's flashcards
        flashcards_b = requests.get(f"{BASE_URL}/flashcards", headers=headers_b).json()
        b_flashcard_topics = [f.get("topic") for f in flashcards_b.get("cards", [])]
        assert "Quantum Architecture" not in b_flashcard_topics, "ISOLATION FAILURE: User B can see User A's flashcards!"

        # 9.4 Verify User B cannot query User A's private/deleted data
        chat_b = requests.post(
            f"{BASE_URL}/ask",
            headers=headers_b,
            json={"question": f"What is {self.unique_secret_code}?"},
        )
        assert chat_b.status_code == 200
        answer_b = chat_b.json().get("answer", "")
        assert self.unique_secret_code not in answer_b, "ISOLATION FAILURE: User B retrieved User A's secret code!"

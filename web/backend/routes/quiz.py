from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from auth_utils import get_current_user_email, create_access_token

import httpx
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from models import (
    GenerateQuizProxyRequest,
    SubmitQuizRequest,
    QuizResult,
)
from database import (
    get_quiz_sessions_collection,
    get_quiz_results_collection,
)
from auth_utils import get_current_user_email

logger = logging.getLogger("uvicorn")
router = APIRouter()

QUIZ_SERVICE_URL = os.getenv("QUIZ_SERVICE_URL", "http://127.0.0.1:8002")


# ---------------- Generate Quiz Proxy ----------------

@router.post("/generate-quiz")
async def generate_quiz_proxy(
    body: GenerateQuizProxyRequest,
    req: Request,
):
    """
    Proxy quiz generation to the AI-ML quiz generator service.
    Persists questions and correct answers in the database (quiz_sessions),
    and filters out answers so the frontend receives ONLY questions without answers.
    """
    # Extract user ID if available from auth header or request
   # Extract user ID if available from auth header or request
    auth_header = req.headers.get("Authorization", "")
    user_id = "anonymous"
    if auth_header.startswith("Bearer "):
        try:
            from auth_utils import decode_access_token
            token = auth_header.split(" ")[1]
            payload_token = decode_access_token(token)
            if payload_token and "sub" in payload_token:
                user_id = payload_token["sub"]
        except Exception:
            pass

    # Ensure internal token is attached for the AI Quiz Generator service
    forward_headers = {
        "Authorization": f"Bearer {create_access_token(user_id)}"
    }

    quiz_type_map = {
        "multiple_choice": "mcq",
        "multiple choice": "mcq",
        "multiple-choice": "mcq",
        "mcq": "mcq",
        "true_false": "true_false",
        "true/false": "true_false",
        "true-false": "true_false",
        "fill_blank": "fill_blank",
        "fill in the blank": "fill_blank",
        "fill_in_the_blank": "fill_blank",
        "short_answer": "short_answer",
        "short answer": "short_answer",
    }
    raw_type = (body.quiz_type or "mcq").lower().strip()
    mapped_quiz_type = quiz_type_map.get(raw_type, raw_type)

    target_url = f"{QUIZ_SERVICE_URL.rstrip('/')}/generate-quiz"
    payload = {
        "topic": body.topic.strip(),
        "question_count": body.question_count,
        "quiz_type": mapped_quiz_type,
    }

    try:
        timeout = httpx.Timeout(
            connect=10.0,
            read=90.0,
            write=10.0,
            pool=10.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(target_url, json=payload, headers=forward_headers)

        if response.status_code == 200:
            data = response.json()
            if not data.get("success", False):
                raise HTTPException(
                    status_code=400,
                    detail=data.get("message", "Failed to generate quiz."),
                )

            raw_questions = data.get("questions", [])
            raw_answers = data.get("answers", [])

            # Generate a secure session ID for grading
            quiz_id = str(uuid.uuid4())

            # Store the session server-side for grading
            quiz_sessions = get_quiz_sessions_collection()
            session_doc = {
                "quiz_id": quiz_id,
                "topic": body.topic.strip(),
                "quiz_type": body.quiz_type,
                "user_id": user_id,
                "questions": raw_questions,
                "answers": raw_answers,
                "created_at": datetime.now(timezone.utc),
            }
            await quiz_sessions.insert_one(session_doc)

            # Filter out answers completely from the frontend payload
            sanitized_questions = []
            for q in raw_questions:
                # Retain only public question properties
                sanitized_q = {
                    "question_id": q.get("question_id"),
                    "question": q.get("question"),
                    "question_type": q.get("question_type", body.quiz_type),
                    "options": q.get("options"),
                    "difficulty": q.get("difficulty", "medium"),
                    "topic": q.get("topic", body.topic),
                }
                sanitized_questions.append(sanitized_q)

            return {
                "success": True,
                "message": data.get("message", f"Generated {len(sanitized_questions)} questions."),
                "quiz_id": quiz_id,
                "topic": body.topic.strip(),
                "quiz_type": body.quiz_type,
                "questions": sanitized_questions,
            }

        # Handle non-200 upstream errors
        error_detail = response.text
        try:
            err_json = response.json()
            if isinstance(err_json, dict) and "detail" in err_json:
                error_detail = err_json["detail"]
            elif isinstance(err_json, dict) and "message" in err_json:
                error_detail = err_json["message"]
        except Exception:
            pass

        raise HTTPException(
            status_code=response.status_code,
            detail=error_detail,
        )

    except HTTPException:
        raise
    except httpx.ReadTimeout as e:
        logger.warning(f"Quiz service timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Quiz generator service took too long to respond. Please try again.",
        )
    except httpx.ConnectError as e:
        logger.warning(f"Quiz service connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Quiz generator service is unavailable. "
                f"Please ensure the quiz generator service is running on {QUIZ_SERVICE_URL}."
            ),
        )
    except Exception as e:
        logger.error(f"Quiz service unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while generating the quiz: {str(e)}",
        )


# ---------------- Server-Side Quiz Grading ----------------

@router.post("/submit-quiz")
async def submit_quiz(
    body: SubmitQuizRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """
    Grades user quiz submission on the server against ground-truth answers
    stored during quiz generation. Saves graded results to quiz history.
    """
    email_clean = current_user_email.strip().lower()

    # Parse submitted answers map {question_id: selected_answer}
    submitted_map: Dict[str, str] = {}
    if isinstance(body.answers, dict):
        submitted_map = {str(k): str(v) for k, v in body.answers.items()}
    elif isinstance(body.answers, list):
        for item in body.answers:
            if isinstance(item, dict):
                qid = str(item.get("question_id", ""))
                ans = str(item.get("selected_answer", item.get("answer", "")))
                if qid:
                    submitted_map[qid] = ans
    elif body.results and isinstance(body.results, list):
        for item in body.results:
            if isinstance(item, dict):
                qid = str(item.get("question_id", ""))
                ans = str(item.get("selected_answer", item.get("answer", "")))
                if qid:
                    submitted_map[qid] = ans

    if not submitted_map:
        raise HTTPException(
            status_code=400,
            detail="No answers provided in submission.",
        )

    quiz_sessions = get_quiz_sessions_collection()
    session_doc = None

    # Retrieve quiz session by quiz_id if provided
    if body.quiz_id:
        session_doc = await quiz_sessions.find_one({"quiz_id": body.quiz_id})

    # Fallback: search by question_ids in session answers
    if not session_doc:
        sample_qids = list(submitted_map.keys())
        session_doc = await quiz_sessions.find_one({
            "answers.question_id": {"$in": sample_qids}
        })

    if not session_doc:
        raise HTTPException(
            status_code=404,
            detail="Quiz session not found. Please regenerate the quiz.",
        )

    stored_answers = session_doc.get("answers", [])
    answers_by_qid = {
        str(a.get("question_id")): a
        for a in stored_answers
        if isinstance(a, dict) and "question_id" in a
    }

    topic = body.topic or session_doc.get("topic", "General")
    graded_records = []
    quiz_results = get_quiz_results_collection()

    for qid, user_answer in submitted_map.items():
        stored_ans_info = answers_by_qid.get(qid, {})
        correct_answer = str(stored_ans_info.get("answer", "")).strip()
        explanation = stored_ans_info.get("explanation")
        user_clean = user_answer.strip()

        # Grade answer with clean case-insensitive comparison
        is_correct = bool(
            correct_answer
            and user_clean.lower() == correct_answer.lower()
        )

        graded_records.append({
            "question_id": qid,
            "topic": topic,
            "selected_answer": user_clean,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": explanation,
        })

        # Save to user quiz history
        record = QuizResult(
            user_id=email_clean,
            question_id=qid,
            topic=topic,
            selected_answer=user_clean,
            correct_answer=correct_answer,
            is_correct=is_correct,
        )
        await quiz_results.insert_one(record.model_dump())

    total_count = len(graded_records)
    correct_count = sum(1 for r in graded_records if r["is_correct"])
    percentage = round((correct_count / total_count) * 100) if total_count > 0 else 0

    return {
        "success": True,
        "score": correct_count,
        "total": total_count,
        "percentage": percentage,
        "results": graded_records,
    }

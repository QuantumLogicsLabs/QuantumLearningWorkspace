import os
import logging
from typing import List, Dict, Any, Optional
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from auth_utils import get_current_user_email
import database
from models import RoadmapNextStep, RoadmapNextStepsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["roadmap"])

ROADMAP_SERVICE_URL = os.getenv("ROADMAP_SERVICE_URL", "http://localhost:8004")

# Curated high-yield fallback steps
DEFAULT_CURATED_STEPS: List[Dict[str, Any]] = [
    {
        "topic": "Quantum Computing & Superposition",
        "description": "Master qubits, quantum entanglement, and superposition principles through active recall.",
        "estimated_duration": "1-2 days",
        "priority": "high",
        "action_label": "Study Flashcards",
        "target_tab": "flashcards",
    },
    {
        "topic": "Machine Learning Foundations",
        "description": "Reinforce core concepts: bias-variance tradeoff, regularization, and transformers.",
        "estimated_duration": "2-3 days",
        "priority": "medium",
        "action_label": "Take Quiz",
        "target_tab": "quiz",
    },
    {
        "topic": "Algorithms & Data Structures",
        "description": "Explore search traversals, tree balancing, and hash table complexities with AI assistant.",
        "estimated_duration": "2 days",
        "priority": "recommended",
        "action_label": "Ask AI Chat",
        "target_tab": "chat",
    },
]


@router.get("/roadmap/next-steps", response_model=RoadmapNextStepsResponse)
@router.get("/roadmap", response_model=RoadmapNextStepsResponse)
async def get_recommended_next_steps(
    authorization: Optional[str] = Header(default=None),
):
    """
    Returns the top 2-3 recommended next steps for the user's dashboard roadmap.
    Pulls from:
    1. Weak topics identified in flashcard reviews or quiz results.
    2. Uploaded study materials and documents.
    3. Curated active learning topics if no activity is recorded yet.
    """
    user_email: Optional[str] = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            from auth_utils import decode_access_token
            payload = decode_access_token(token)
            if payload:
                user_email = payload.get("sub")
        except Exception:
            pass

    next_steps: List[RoadmapNextStep] = []

    if user_email:
        user_id = user_email.strip().lower()
        weak_topics = []
        recent_uploads_titles = []

        # 1. Pull weak topics from flashcard reviews
        try:
            reviews_col = database.get_flashcard_reviews_collection()
            cursor = reviews_col.find({"user_id": user_id})
            topic_aggregates: Dict[str, Dict[str, int]] = {}

            async for doc in cursor:
                t = doc.get("topic", "General")
                st = doc.get("status")
                if t not in topic_aggregates:
                    topic_aggregates[t] = {"known": 0, "still_learning": 0, "total": 0}
                topic_aggregates[t]["total"] += 1
                if st == "known":
                    topic_aggregates[t]["known"] += 1
                elif st == "still_learning":
                    topic_aggregates[t]["still_learning"] += 1

            # Identify weak topics
            for t_name, stats in topic_aggregates.items():
                if stats["still_learning"] > stats["known"] or (
                    stats["total"] >= 2 and (stats["known"] / stats["total"]) < 0.6
                ):
                    weak_topics.append(t_name)
        except Exception:
            pass

        # 2. Check user's recent uploads
        try:
            uploads_col = database.get_uploads_collection()
            recent_upload = await uploads_col.find_one(
                {"user_id": user_id, "status": "Ready"},
                sort=[("upload_date", -1)],
            )
            if recent_upload and recent_upload.get("filename"):
                clean_title = recent_upload["filename"].replace(".pdf", "").replace("_", " ").title()
                recent_uploads_titles.append(clean_title)
        except Exception:
            pass

        has_user_activity = bool(weak_topics or recent_uploads_titles)

        # 3. Call Team Lambda Roadmap Generator API (Port 8004) if live & available
        if authorization and not os.environ.get("PYTEST_CURRENT_TEST"):
            candidate_topics: List[str] = []
            priorities_map: Dict[str, str] = {}

            if has_user_activity:
                # Strictly use the user's actual weak topics and uploads (NO placeholders)
                for wt in weak_topics:
                    candidate_topics.append(wt)
                    priorities_map[wt] = "high"

                for up in recent_uploads_titles:
                    if up not in candidate_topics:
                        candidate_topics.append(up)
                        priorities_map[up] = "normal"
            else:
                # Brand new user with no activity: use curated topics
                for curated in DEFAULT_CURATED_STEPS:
                    candidate_topics.append(curated["topic"])
                    priorities_map[curated["topic"]] = curated["priority"]

            if candidate_topics:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.post(
                            f"{ROADMAP_SERVICE_URL}/generate-roadmap",
                            json={
                                "topic_names": candidate_topics,
                                "subject": "Personalized Study Roadmap",
                                "step_count": min(max(len(candidate_topics), 3), 5) if not has_user_activity else max(len(candidate_topics), 2),
                                "priorities": priorities_map,
                            },
                            headers={
                                "Authorization": authorization,
                                "Content-Type": "application/json",
                            },
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            raw_steps = data.get("steps", [])
                            if raw_steps:
                                lambda_steps: List[RoadmapNextStep] = []
                                for idx, s in enumerate(raw_steps):
                                    t_name = s.get("topic", "")
                                    desc = s.get("description", "")
                                    dur = s.get("estimated_duration") or "1-2 days"

                                    # Categorize step
                                    is_weak = any(wt.lower() in t_name.lower() for wt in weak_topics) or (idx == 0 and bool(weak_topics))
                                    is_upload = any(up.lower() in t_name.lower() for up in recent_uploads_titles)

                                    if is_weak:
                                        prio = "high"
                                        action = "Review Flashcards"
                                        tab = "flashcards"
                                    elif is_upload:
                                        prio = "medium"
                                        action = "Take Quiz"
                                        tab = "quiz"
                                    else:
                                        prio = "recommended"
                                        action = "Take Quiz" if idx % 2 == 0 else "Study Flashcards"
                                        tab = "quiz" if idx % 2 == 0 else "flashcards"

                                    lambda_steps.append(
                                        RoadmapNextStep(
                                            step_number=s.get("step_number", idx + 1),
                                            topic=t_name,
                                            description=desc,
                                            estimated_duration=dur,
                                            priority=prio,
                                            action_label=action,
                                            target_tab=tab,
                                        )
                                    )

                                return RoadmapNextStepsResponse(
                                    success=True,
                                    user_id=user_email,
                                    subject=data.get("subject") or "Your Personalized Study Roadmap",
                                    total_steps=len(lambda_steps),
                                    next_steps=lambda_steps,
                                )
                except Exception as exc:
                    logger.warning("Team Lambda Roadmap Generator unavailable or error (%s), using curated fallback.", exc)

        # 4. Fallback synthesis (used if Lambda service is offline, unauthenticated, or in test mode)
        if has_user_activity:
            # User has activity: build steps ONLY from weak topics and uploads (NO placeholders)
            for wt in weak_topics[:3]:
                next_steps.append(
                    RoadmapNextStep(
                        step_number=len(next_steps) + 1,
                        topic=f"Review Weak Topic: {wt}",
                        description=f"You marked questions in '{wt}' as needing practice. Strengthen your recall now.",
                        estimated_duration="1 day",
                        priority="high",
                        action_label="Review Flashcards",
                        target_tab="flashcards",
                    )
                )

            for up in recent_uploads_titles[:2]:
                if len(next_steps) >= 3:
                    break
                next_steps.append(
                    RoadmapNextStep(
                        step_number=len(next_steps) + 1,
                        topic=f"Test Knowledge: {up}",
                        description=f"Generate a customized quiz or practice flashcards from your uploaded file '{up}'.",
                        estimated_duration="1-2 days",
                        priority="medium",
                        action_label="Take Quiz",
                        target_tab="quiz",
                    )
                )

            # If user has only 1 weak topic and no uploads, create reinforcement step for that same weak topic
            if len(next_steps) == 1 and weak_topics:
                wt = weak_topics[0]
                next_steps.append(
                    RoadmapNextStep(
                        step_number=2,
                        topic=f"Test Mastery: {wt}",
                        description=f"Validate your understanding of '{wt}' with an active practice quiz.",
                        estimated_duration="1-2 days",
                        priority="medium",
                        action_label="Take Quiz",
                        target_tab="quiz",
                    )
                )

    # 5. Curated default placeholders are ONLY shown if user has ZERO activity (next_steps is still empty)
    if not next_steps:
        for item in DEFAULT_CURATED_STEPS:
            next_steps.append(
                RoadmapNextStep(
                    step_number=len(next_steps) + 1,
                    topic=item["topic"],
                    description=item["description"],
                    estimated_duration=item["estimated_duration"],
                    priority=item["priority"],
                    action_label=item["action_label"],
                    target_tab=item["target_tab"],
                )
            )

    return RoadmapNextStepsResponse(
        success=True,
        user_id=user_email or "guest",
        subject="Your Personalized Study Roadmap",
        total_steps=len(next_steps),
        next_steps=next_steps[:3],
    )

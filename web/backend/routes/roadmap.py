from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from auth_utils import get_current_user_email
import database
from models import RoadmapNextStep, RoadmapNextStepsResponse

router = APIRouter(tags=["roadmap"])

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
            weak_topics = []
            for t_name, stats in topic_aggregates.items():
                if stats["still_learning"] > stats["known"] or (
                    stats["total"] >= 2 and (stats["known"] / stats["total"]) < 0.6
                ):
                    weak_topics.append(t_name)

            for wt in weak_topics[:2]:
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
        except Exception:
            pass

        # 2. Check user's recent uploads
        if len(next_steps) < 3:
            try:
                uploads_col = database.get_uploads_collection()
                recent_upload = await uploads_col.find_one(
                    {"user_id": user_id, "status": "Ready"},
                    sort=[("upload_date", -1)],
                )
                if recent_upload and recent_upload.get("filename"):
                    clean_title = recent_upload["filename"].replace(".pdf", "").replace("_", " ").title()
                    next_steps.append(
                        RoadmapNextStep(
                            step_number=len(next_steps) + 1,
                            topic=f"Test Knowledge: {clean_title}",
                            description=f"Generate a customized quiz or practice flashcards from your uploaded file '{recent_upload['filename']}'.",
                            estimated_duration="1-2 days",
                            priority="medium",
                            action_label="Take Quiz",
                            target_tab="quiz",
                        )
                    )
            except Exception:
                pass

    # 3. Fill remaining slots with curated high-yield defaults up to 3
    default_idx = 0
    while len(next_steps) < 3 and default_idx < len(DEFAULT_CURATED_STEPS):
        item = DEFAULT_CURATED_STEPS[default_idx]
        # Avoid duplicate topic names
        if not any(item["topic"].lower() in s.topic.lower() for s in next_steps):
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
        default_idx += 1

    return RoadmapNextStepsResponse(
        success=True,
        user_id=user_email or "guest",
        subject="Your Personalized Study Roadmap",
        total_steps=len(next_steps),
        next_steps=next_steps[:3],  # Ensure top 2-3 items
    )

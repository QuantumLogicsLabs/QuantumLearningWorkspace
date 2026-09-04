import os
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Header, status
from auth_utils import get_current_user_email
import database
from models import (
    Flashcard,
    GenerateFlashcardsRequest,
    GenerateFlashcardsResponse,
    FlashcardReviewRequest,
    FlashcardReview,
    WeakTopicSummary,
    TopicReviewStatsResponse,
)

router = APIRouter(tags=["flashcards"])

# ==========================================
# Flashcard Generator Engine (Synthetic & Fallback)
# ==========================================
TOPIC_KNOWLEDGE_BASE: Dict[str, List[Dict[str, str]]] = {
    "quantum computing": [
        {
            "front": "What is a Qubit?",
            "back": "A qubit (quantum bit) is the basic unit of quantum information, capable of existing in a state of 0, 1, or any quantum superposition of both.",
        },
        {
            "front": "What is Quantum Superposition?",
            "back": "The principle that a quantum system can exist in multiple states simultaneously until it is measured.",
        },
        {
            "front": "Explain Quantum Entanglement.",
            "back": "A phenomenon where two or more quantum particles become strongly interconnected such that the state of one instantly dictates the state of the other, regardless of distance.",
        },
        {
            "front": "What is the role of a Hadamard (H) Gate in quantum circuits?",
            "back": "The Hadamard gate creates an equal superposition of |0⟩ and |1⟩ states from a standard basis state.",
        },
        {
            "front": "What is Quantum Decoherence?",
            "back": "The loss of quantum coherence where a quantum system interacts with its environment, causing superposition states to decay into classical states.",
        },
        {
            "front": "What is Shor's Algorithm?",
            "back": "A quantum algorithm for integer factorization that runs in polynomial time, posing a theoretical challenge to RSA encryption.",
        },
    ],
    "machine learning": [
        {
            "front": "What is Overfitting and how can it be prevented?",
            "back": "Overfitting happens when a model learns noise in training data. It is mitigated by regularization (L1/L2), dropout, cross-validation, and pruning.",
        },
        {
            "front": "What is the Bias-Variance Tradeoff?",
            "back": "High bias leads to underfitting (oversimplified model), while high variance leads to overfitting. Optimal models balance both for low generalization error.",
        },
        {
            "front": "Explain the difference between Supervised and Unsupervised Learning.",
            "back": "Supervised learning uses labeled training datasets with ground-truth targets, whereas unsupervised learning discovers patterns and groupings without predefined labels.",
        },
        {
            "front": "What is Backpropagation?",
            "back": "An optimization algorithm that computes the gradient of the loss function with respect to neural network weights using the chain rule.",
        },
        {
            "front": "What is the Attention Mechanism in Transformers?",
            "back": "A technique that allows models to dynamically weigh the importance of different tokens in a sequence relative to each other.",
        },
    ],
    "python": [
        {
            "front": "What is the Global Interpreter Lock (GIL) in CPython?",
            "back": "A mutex that protects access to Python objects, preventing multiple native threads from executing Python bytecodes concurrently in a single process.",
        },
        {
            "front": "What is the difference between mutable and immutable types in Python?",
            "back": "Immutable types (e.g. str, int, tuple) cannot be modified after creation; mutable types (e.g. list, dict, set) can have their contents altered in place.",
        },
        {
            "front": "How do Python generators work and what is the 'yield' keyword?",
            "back": "Generators produce items lazily on demand using the 'yield' keyword, maintaining execution state with minimal memory overhead.",
        },
        {
            "front": "What are Python Decorators?",
            "back": "Functions that take another function as an argument, extend or modify its behavior, and return a callable object.",
        },
    ],
    "data structures": [
        {
            "front": "What is the average and worst-case time complexity of Hash Table lookup?",
            "back": "Average time complexity is O(1); worst-case complexity is O(n) when hash collisions degrade the table to a linked list.",
        },
        {
            "front": "What is the difference between BFS and DFS traversal?",
            "back": "Breadth-First Search (BFS) explores neighbor nodes layer by layer using a Queue. Depth-First Search (DFS) explores as deep as possible along each branch using a Stack/Recursion.",
        },
        {
            "front": "What are the properties of a Red-Black Tree?",
            "back": "A self-balancing binary search tree where every node is red or black, the root is black, red nodes cannot have red children, and every path from root to leaf contains equal black nodes.",
        },
    ],
}

def _generate_synthetic_cards(topic: str, count: int, difficulty: str, content: Optional[str] = None) -> List[Flashcard]:
    """Generate high quality topic-based flashcards."""
    normalized_topic = topic.strip().lower()
    cards: List[Flashcard] = []
    
    # If custom content was provided
    if content and len(content.strip()) > 20:
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        for line in lines[:count]:
            card_id = str(uuid.uuid4())
            if ":" in line:
                term, defn = line.split(":", 1)
                front = f"What is {term.strip()} in the context of {topic}?"
                back = defn.strip()
            elif "?" in line:
                front = line
                back = f"Key principle related to {topic}."
            else:
                front = f"Explain the core concept: '{line[:80]}...'"
                back = f"{line} (Relevant to {topic})"
            
            cards.append(
                Flashcard(
                    id=card_id,
                    front=front,
                    back=back,
                    question=front,
                    answer=back,
                    topic=topic,
                    difficulty=difficulty,
                )
            )

    # Predefined domain knowledge
    if len(cards) < count:
        matched_kb = None
        for key in TOPIC_KNOWLEDGE_BASE:
            if key in normalized_topic or normalized_topic in key:
                matched_kb = TOPIC_KNOWLEDGE_BASE[key]
                break

        if matched_kb:
            for item in matched_kb:
                if len(cards) >= count:
                    break
                card_id = str(uuid.uuid4())
                cards.append(
                    Flashcard(
                        id=card_id,
                        front=item["front"],
                        back=item["back"],
                        question=item["front"],
                        answer=item["back"],
                        topic=topic,
                        difficulty=difficulty,
                    )
                )

    # Heuristic templates fallback
    templates = [
        ("What is the primary definition and scope of {topic}?", 
         "{topic} is an essential domain focusing on core principles, methodologies, and practical applications in modern problem-solving."),
        ("What are the key foundational pillars of {topic}?", 
         "The fundamental components of {topic} encompass theoretical foundations, systematic workflows, and empirical validation."),
        ("What common pitfalls or misconceptions occur in {topic}?", 
         "A frequent misconception in {topic} is confusing high-level abstractions with underlying implementation constraints and edge cases."),
        ("How is {topic} applied in real-world production environments?", 
         "In production, {topic} is leveraged to optimize performance, enhance reliability, and solve domain-specific scalability challenges."),
        ("What are the best practices for mastering and evaluating {topic}?", 
         "Best practices include active recall, structured problem sets, continuous code/concept review, and modular architecture design."),
    ]
    
    template_idx = 0
    while len(cards) < count:
        q_tpl, a_tpl = templates[template_idx % len(templates)]
        card_id = str(uuid.uuid4())
        front = q_tpl.format(topic=topic.title())
        back = a_tpl.format(topic=topic.title())
        cards.append(
            Flashcard(
                id=card_id,
                front=front,
                back=back,
                question=front,
                answer=back,
                topic=topic,
                difficulty=difficulty,
            )
        )
        template_idx += 1

    return cards[:count]

# ==========================================
# Endpoints
# ==========================================

@router.post("/generate-flashcards", response_model=GenerateFlashcardsResponse)
@router.post("/flashcards/generate", response_model=GenerateFlashcardsResponse)
async def generate_flashcards(
    request: GenerateFlashcardsRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """
    Topic-based flashcard generation endpoint.
    Returns generated flashcards with unique id, question/front, and answer/back.
    """
    if not request.topic or not request.topic.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic must not be empty.",
        )

    num_cards = request.num_cards or 5
    num_cards = max(1, min(num_cards, 20))
    difficulty = request.difficulty or "medium"

    cards = _generate_synthetic_cards(
        topic=request.topic.strip(),
        count=num_cards,
        difficulty=difficulty,
        content=request.content,
    )

    return GenerateFlashcardsResponse(
        success=True,
        topic=request.topic.strip(),
        total_cards=len(cards),
        cards=cards,
    )

@router.post("/flashcards/review")
async def review_flashcard(
    request: FlashcardReviewRequest,
    current_user_email: str = Depends(get_current_user_email),
):
    """
    Track flashcard review status ('known' vs 'still_learning') and save in
    MongoDB collection 'flashcard_reviews'.
    """
    if request.status not in ("known", "still_learning"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid status. Status must be either 'known' or 'still_learning'.",
        )

    user_id = current_user_email.strip().lower()
    is_weak = (request.status == "still_learning")

    review = FlashcardReview(
        user_id=user_id,
        flashcard_id=request.flashcard_id,
        topic=request.topic.strip(),
        status=request.status,
        date_reviewed=datetime.now(timezone.utc),
        item_type="flashcard",
        is_weak=is_weak,
    )

    reviews_col = database.get_flashcard_reviews_collection()
    insert_result = await reviews_col.insert_one(review.model_dump())
    inserted_id = getattr(insert_result, "inserted_id", None)

    return {
        "message": "Review tracked successfully.",
        "review_id": str(inserted_id) if inserted_id else str(uuid.uuid4()),
        "user_id": user_id,
        "flashcard_id": review.flashcard_id,
        "topic": review.topic,
        "status": review.status,
        "is_weak": review.is_weak,
        "date_reviewed": review.date_reviewed.isoformat(),
    }

@router.get("/flashcards/reviews")
async def get_user_reviews(
    topic: Optional[str] = None,
    current_user_email: str = Depends(get_current_user_email),
):
    """Fetch review history for the authenticated user, optionally filtered by topic."""
    user_id = current_user_email.strip().lower()
    reviews_col = database.get_flashcard_reviews_collection()
    query: Dict[str, Any] = {"user_id": user_id}
    if topic:
        query["topic"] = topic

    cursor = reviews_col.find(query).sort("date_reviewed", -1)
    reviews_list = []
    async for doc in cursor:
        doc["_id"] = str(doc.get("_id", ""))
        reviews_list.append(doc)

    return {
        "user_id": user_id,
        "total_reviews": len(reviews_list),
        "reviews": reviews_list,
    }

@router.get("/flashcards/weak-topics", response_model=TopicReviewStatsResponse)
async def get_weak_topics(
    current_user_email: str = Depends(get_current_user_email),
):
    """
    Compute weak topics based on review status ('still_learning' vs 'known')
    aligned with quiz results schema for unified weakness detection.
    """
    user_id = current_user_email.strip().lower()
    reviews_col = database.get_flashcard_reviews_collection()
    cursor = reviews_col.find({"user_id": user_id})

    topic_aggregates: Dict[str, Dict[str, int]] = {}
    total_reviews = 0

    async for doc in cursor:
        total_reviews += 1
        t = doc.get("topic", "General")
        st = doc.get("status")
        if t not in topic_aggregates:
            topic_aggregates[t] = {"known": 0, "still_learning": 0, "total": 0}
        
        topic_aggregates[t]["total"] += 1
        if st == "known":
            topic_aggregates[t]["known"] += 1
        elif st == "still_learning":
            topic_aggregates[t]["still_learning"] += 1

    weak_topics_list: List[WeakTopicSummary] = []
    for t_name, stats in topic_aggregates.items():
        tot = stats["total"]
        k = stats["known"]
        sl = stats["still_learning"]
        mastery = round(k / tot, 2) if tot > 0 else 0.0
        
        is_weak = (sl > k) or (tot >= 2 and mastery < 0.6)

        weak_topics_list.append(
            WeakTopicSummary(
                topic=t_name,
                total_reviews=tot,
                known_count=k,
                still_learning_count=sl,
                mastery_score=mastery,
                is_weak=is_weak,
            )
        )

    weak_topics_list.sort(key=lambda x: (not x.is_weak, x.mastery_score))

    return TopicReviewStatsResponse(
        user_id=user_id,
        weak_topics=weak_topics_list,
        total_reviews=total_reviews,
    )

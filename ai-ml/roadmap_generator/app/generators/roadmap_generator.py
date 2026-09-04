import json

from groq import Groq

from roadmap_generator.app.generators.base_generator import BaseGenerator
from roadmap_generator.app.config import GROQ_API_KEY, GROQ_MODEL, DEFAULT_STEP_COUNT
from roadmap_generator.app.models.topic import Topic
from roadmap_generator.app.models.roadmap import Roadmap, RoadmapStep


class RoadmapGenerator(BaseGenerator):
    """
    Generates a simple, ordered study roadmap for a subject or set of
    topics using the Groq API. General-purpose: does not depend on
    Weak-topic Detection or any other module's output.
    """

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate(
        self,
        topics: list[Topic],
        subject: str = "",
        step_count: int = DEFAULT_STEP_COUNT,
    ) -> Roadmap:
        if not topics:
            raise ValueError("At least one topic is required to generate a roadmap.")

        topic_lines = []
        for t in topics:
            line = f"- {t.name}"
            if t.description:
                line += f" ({t.description})"
            if t.priority:
                line += f" [priority: {t.priority}]"
            topic_lines.append(line)
        topics_block = "\n".join(topic_lines)

        subject_label = subject or ", ".join(t.name for t in topics)

        prompt = f"""
        Create a simple, ordered study roadmap for the following subject/topics.

        Subject: {subject_label}

        Topics to cover:
        {topics_block}

        Rules:
        - Produce exactly {step_count} sequential steps.
        - Each step should build logically on the previous one (foundational
          concepts before advanced ones).
        - Keep each step's description concise and actionable (1-2 sentences).
        - Give a rough estimated_duration for each step (e.g. "2-3 days"),
          as a general suggestion, not a strict deadline.
        - If a topic has a stated priority of "high", make sure it is covered
          reasonably early in the roadmap, but the roadmap should still make
          logical sense as a learning sequence.

        Respond with ONLY a JSON array, no other text, in this exact shape:
        [
          {{
            "step_number": 1,
            "topic": "...",
            "description": "...",
            "estimated_duration": "..."
          }}
        ]
        """

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )

        raw = response.choices[0].message.content or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"RoadmapGenerator: could not parse LLM response as JSON: {exc}"
            ) from exc

        steps = [
            RoadmapStep(
                step_number=item.get("step_number", idx + 1),
                topic=item["topic"],
                description=item["description"],
                estimated_duration=item.get("estimated_duration"),
            )
            for idx, item in enumerate(items)
        ]

        return Roadmap(subject=subject_label, steps=steps, total_steps=len(steps))

from typing import Optional

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """
    Represents a single subject/topic used as input for roadmap
    generation. Deliberately generic: this module does not depend on
    Weak-topic Detection, but a caller (e.g. a future integration)
    could populate `priority` from weak-topic results without this
    module needing to know anything about that source.
    """

    name: str = Field(..., min_length=1, description="Topic or subject name.")

    description: Optional[str] = Field(
        default=None,
        description="Optional extra context about the topic to guide generation.",
    )

    priority: Optional[str] = Field(
        default=None,
        description="Optional hint: 'high', 'normal', 'low'. Not required.",
    )

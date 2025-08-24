import logging
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class BaseEvent(BaseModel):
    """Base class for all events"""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scope: Optional[str] = None
    trajectory_id: Optional[str] = None
    project_id: Optional[str] = None
    event_type: str
    data: Optional[dict] = Field(default_factory=dict)

    model_config = {"ser_json_timedelta": "iso8601", "json_encoders": {datetime: lambda dt: dt.isoformat()}}

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

    @classmethod
    def from_dict(cls, data: dict) -> "BaseEvent":
        """Create an event from a dictionary."""
        return cls.model_validate(data)


class FlowEvent(BaseEvent):
    scope: str = "flow"


class FlowStartedEvent(FlowEvent):
    """Flow-specific event"""

    event_type: str = "started"


class FlowCompletedEvent(FlowEvent):
    """Flow-specific event"""

    event_type: str = "completed"


class ProgressEvent(BaseEvent):
    """Progress tracking event for long-running operations"""
    
    scope: str = "progress"
    event_type: str = "progress"
    operation_id: str
    progress_percentage: float = Field(ge=0, le=100)
    current_step: str
    total_steps: int
    estimated_remaining_time: Optional[float] = None


class CodeAnalysisEvent(BaseEvent):
    """Code analysis progress event"""
    
    scope: str = "code_analysis"
    event_type: str = "analysis"
    file_path: str
    analysis_type: str  # "syntax", "semantic", "quality", "security"
    status: str  # "started", "completed", "error"
    results: Optional[dict] = None


class ConversationEvent(BaseEvent):
    """Conversation and dialogue events"""
    
    scope: str = "conversation"
    event_type: str = "message"
    conversation_id: str
    message_type: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[dict] = None


class ProjectEvent(BaseEvent):
    """Project-level events"""
    
    scope: str = "project"
    event_type: str = "status_update"
    status: str  # "active", "paused", "completed", "error"
    details: Optional[dict] = None


class SecurityScanEvent(BaseEvent):
    """Security scanning events"""
    
    scope: str = "security"
    event_type: str = "scan"
    scan_type: str  # "vulnerability", "dependency", "secrets"
    file_path: Optional[str] = None
    severity: str  # "low", "medium", "high", "critical"
    finding: dict


class FlowErrorEvent(FlowEvent):
    event_type: str = "error"

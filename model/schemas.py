from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConversationMetadata:
    sender_id: str = "unknown_sender"
    conversation_id: str = ""
    friendship_duration_days: int = 0
    sender_age: int = 25
    receiver_age: int = 25

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]] = None) -> "ConversationMetadata":
        data = data or {}
        return cls(
            sender_id=data.get("sender_id", "unknown_sender"),
            conversation_id=data.get("conversation_id", ""),
            friendship_duration_days=int(data.get("friendship_duration_days", 0)),
            sender_age=int(data.get("sender_age", 25)),
            receiver_age=int(data.get("receiver_age", 25)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MessageAnalysis:
    text: str
    sender: str = "unknown"
    toxicity: float = 0.0
    sentiment: float = 0.0
    toxicity_source: Optional[str] = None
    sentiment_source: Optional[str] = None
    image_base64: Optional[str] = None
    is_nsfw_image: bool = False
    nsfw_score: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageAnalysis":
        return cls(
            text=data.get("text", ""),
            sender=data.get("sender", "unknown"),
            toxicity=float(data.get("toxicity", 0.0)),
            sentiment=float(data.get("sentiment", 0.0)),
            toxicity_source=data.get("toxicity_source"),
            sentiment_source=data.get("sentiment_source"),
            image_base64=data.get("image_base64"),
            is_nsfw_image=bool(data.get("is_nsfw_image", False)),
            nsfw_score=float(data.get("nsfw_score", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


@dataclass
class PatternEvidence:
    flag: str
    message_indices: List[int] = field(default_factory=list)
    matched_text: List[str] = field(default_factory=list)
    detail: str = ""
    weight: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PatternMatchResult:
    flags: List[str] = field(default_factory=list)
    detected_phase: str = "Normal"
    evidence: List[PatternEvidence] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "flags": list(self.flags),
            "detected_phase": self.detected_phase,
            "evidence": [item.to_dict() for item in self.evidence],
            "category_scores": dict(self.category_scores),
        }


@dataclass
class ConversationFeatures:
    avg_toxicity: float = 0.0
    max_toxicity: float = 0.0
    num_toxic_messages: int = 0
    max_consecutive_toxic: int = 0
    sender_imbalance: float = 0.0
    escalation: float = 0.0
    age_disparity: float = 0.0
    is_long_friendship: float = 0.0
    phase_score: float = 0.0
    secrecy_score: float = 0.0
    pii_request_score: float = 0.0
    boundary_pressure_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionResult:
    risk_level: str = "safe"
    confidence: float = 0.0
    repeat_offender: bool = False
    category_scores: Dict[str, float] = field(default_factory=dict)
    decision_trace: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    risk_level: str
    confidence: float
    reason: str
    flagged_messages: List[int] = field(default_factory=list)
    behavioral_flags: List[str] = field(default_factory=list)
    detected_phase: str = "Normal"
    evidence: List[PatternEvidence] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    decision_trace: List[str] = field(default_factory=list)
    user_risk_score: int = 0
    repeat_offender: bool = False
    ai_judgment: str = ""
    threat_category: str = "unknown"
    action_recommended: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "reason": self.reason,
            "flagged_messages": list(self.flagged_messages),
            "behavioral_flags": list(self.behavioral_flags),
            "detected_phase": self.detected_phase,
            "evidence": [item.to_dict() for item in self.evidence],
            "category_scores": dict(self.category_scores),
            "decision_trace": list(self.decision_trace),
            "user_risk_score": self.user_risk_score,
            "repeat_offender": self.repeat_offender,
            "ai_judgment": self.ai_judgment,
            "threat_category": self.threat_category,
            "action_recommended": self.action_recommended,
        }

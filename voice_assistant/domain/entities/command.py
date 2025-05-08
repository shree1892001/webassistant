from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Command:
    """Represents a user command with its analysis results"""
    intent: str
    action: str
    target: str
    parameters: Dict[str, Any]
    confidence: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Command':
        """Create a Command instance from a dictionary"""
        return cls(
            intent=data.get('intent', 'unknown'),
            action=data.get('action', 'unknown'),
            target=data.get('target', 'unknown'),
            parameters=data.get('parameters', {}),
            confidence=data.get('confidence', 0.0)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Command instance to dictionary"""
        return {
            'intent': self.intent,
            'action': self.action,
            'target': self.target,
            'parameters': self.parameters,
            'confidence': self.confidence
        } 
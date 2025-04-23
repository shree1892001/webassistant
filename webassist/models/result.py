"""
Result models for WebAssist
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class InteractionResult:
    """Result of an interaction attempt"""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "message": self.message,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractionResult':
        """Create from dictionary"""
        return cls(
            success=data.get("success", False),
            message=data.get("message", ""),
            details=data.get("details")
        )
    
    @classmethod
    def success_result(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'InteractionResult':
        """Create a success result"""
        return cls(True, message, details)
    
    @classmethod
    def failure_result(cls, message: str, details: Optional[Dict[str, Any]] = None) -> 'InteractionResult':
        """Create a failure result"""
        return cls(False, message, details)

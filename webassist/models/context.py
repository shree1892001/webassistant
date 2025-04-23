"""
Context models for WebAssist
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class InteractionContext:
    """Context for element interactions"""
    purpose: str
    element_type: str
    action: str
    value: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    product_name: Optional[str] = None
    element_id: Optional[str] = None
    element_classes: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "purpose": self.purpose,
            "element_type": self.element_type,
            "action": self.action,
            "value": self.value,
            "options": self.options,
            "product_name": self.product_name,
            "element_id": self.element_id,
            "element_classes": self.element_classes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractionContext':
        """Create from dictionary"""
        return cls(
            purpose=data.get("purpose", ""),
            element_type=data.get("element_type", ""),
            action=data.get("action", ""),
            value=data.get("value"),
            options=data.get("options"),
            product_name=data.get("product_name"),
            element_id=data.get("element_id"),
            element_classes=data.get("element_classes")
        )


@dataclass
class PageContext:
    """Context for a web page"""
    url: str
    title: str
    text: str
    html: str
    input_fields: List[Dict[str, str]] = None
    menu_items: List[Dict[str, Any]] = None
    buttons: List[Dict[str, str]] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.input_fields is None:
            self.input_fields = []
        if self.menu_items is None:
            self.menu_items = []
        if self.buttons is None:
            self.buttons = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "html": self.html,
            "input_fields": self.input_fields,
            "menu_items": self.menu_items,
            "buttons": self.buttons
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PageContext':
        """Create from dictionary"""
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            text=data.get("text", ""),
            html=data.get("html", ""),
            input_fields=data.get("input_fields", []),
            menu_items=data.get("menu_items", []),
            buttons=data.get("buttons", [])
        )

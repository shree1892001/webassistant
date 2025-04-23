"""
Gemini LLM provider for WebAssist
"""

import json
import re
from typing import Dict, Any, List, Optional

import google.generativeai as genai
from webassist.Common.constants import GEMINI_MODEL
from webassist.llm.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini LLM provider"""

    def __init__(self, api_key: str, model: Optional[str] = None):
        """Initialize the provider"""
        genai.configure(api_key=api_key)
        self.model_name = model or GEMINI_MODEL
        self.model = genai.GenerativeModel(self.model_name)

    async def generate_content(self, prompt: str) -> Any:
        """Generate content using Gemini"""
        return self.model.generate_content(prompt)

    async def get_structured_guidance(self, prompt: str) -> Dict[str, Any]:
        """Get structured guidance from Gemini"""
        try:
            response = await self.generate_content(prompt)
            response_text = response.text

            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)

            # If no JSON found, try to extract a list
            list_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if list_match:
                list_str = list_match.group(0)
                return {"selectors": json.loads(list_str)}

            # If no structured data found, return the raw text
            return {"text": response_text}
        except Exception as e:
            print(f"Error getting structured guidance: {e}")
            return {"error": str(e)}

    async def get_selectors(self, prompt: str, context: Dict[str, Any]) -> List[str]:
        """Get selectors from Gemini"""
        try:
            # Create a prompt that includes the context
            full_prompt = f"""
Based on the current web page context, generate the 5 most likely CSS selectors to {prompt}.
Focus on precise selectors that would uniquely identify the element.

Current Page:
Title: {context.get('title', 'N/A')}
URL: {context.get('url', 'N/A')}

Input Fields Found:
{self._format_input_fields(context.get('input_fields', []))}

Menu Items Found:
{self._format_menu_items(context.get('menu_items', []))}

Relevant HTML:
{context.get('html', '')[:1000]}

IMPORTANT: If this appears to be a PrimeNG component (classes containing p-dropdown, p-component, etc.),
prioritize selectors that target PrimeNG specific elements:
- Dropdown: .p-dropdown, .p-dropdown-trigger
- Panel: .p-dropdown-panel
- Items: .p-dropdown-item, .p-dropdown-items li
- Filter: .p-dropdown-filter

Respond ONLY with a JSON array of selector strings. Example:
["selector1", "selector2", "selector3", "selector4", "selector5"]
"""

            # Generate the response
            response = await self.generate_content(full_prompt)

            # Extract the selectors
            selectors_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if selectors_match:
                selectors_json = selectors_match.group(0)
                selectors = json.loads(selectors_json)
                return selectors[:5]
            else:
                return []
        except Exception as e:
            print(f"Selector generation error: {e}")
            return []

    def _format_input_fields(self, input_fields: List[Dict[str, str]]) -> str:
        """Format input fields for LLM prompt"""
        result = ""
        for idx, field in enumerate(input_fields):
            result += f"{idx + 1}. {field.get('tag', 'input')} - "
            result += f"type: {field.get('type', '')}, "
            result += f"id: {field.get('id', '')}, "
            result += f"name: {field.get('name', '')}, "
            result += f"placeholder: {field.get('placeholder', '')}, "
            result += f"aria-label: {field.get('aria-label', '')}\n"
        return result

    def _format_menu_items(self, menu_items: List[Dict[str, Any]]) -> str:
        """Format menu items for LLM prompt"""
        result = ""
        for idx, item in enumerate(menu_items):
            submenu_indicator = " (has submenu)" if item.get("has_submenu") else ""
            result += f"{idx + 1}. {item.get('text', '')}{submenu_indicator}\n"
        return result

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

    def generate_content(self, prompt: str) -> Any:
        """Generate content using Gemini"""
        return self.model.generate_content(prompt)

    async def get_structured_guidance(self, prompt: str) -> Dict[str, Any]:
        """Get structured guidance from Gemini"""
        try:
            response = self.generate_content(prompt)
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

Return ONLY a JSON array of selector strings."""

            response = self.model.generate_content(full_prompt)

            # Handle both string and structured responses
            if isinstance(response.text, str):
                try:
                    # Try to parse as JSON
                    selectors = json.loads(response.text)
                    if isinstance(selectors, list):
                        return selectors
                    return []
                except json.JSONDecodeError:
                    # If not valid JSON, split by newlines and clean up
                    return [s.strip() for s in response.text.split('\n') if s.strip()]

            return []

        except Exception as e:
            print(f"Error generating selectors: {e}")
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

    def _format_buttons(self, buttons: List[Dict[str, Any]]) -> str:
        """Format buttons for LLM prompt"""
        result = ""
        for idx, button in enumerate(buttons):
            result += f"{idx + 1}. {button.get('text', '')} - "
            result += f"id: {button.get('id', '')}, "
            result += f"class: {button.get('class', '')}, "
            result += f"type: {button.get('type', '')}\n"
        return result

    async def get_actions(self, command: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get actions for a command based on page context"""
        try:
            # Format the context information
            input_fields_info = ""
            if "input_fields" in context and context["input_fields"]:
                input_fields_info = "Input Fields Found:\n"
                input_fields_info += self._format_input_fields(context["input_fields"])

            menu_items_info = ""
            if "menu_items" in context and context["menu_items"]:
                menu_items_info = "Menu Items Found:\n"
                menu_items_info += self._format_menu_items(context["menu_items"])

            buttons_info = ""
            if "buttons" in context and context["buttons"]:
                buttons_info = "Buttons Found:\n"
                buttons_info += self._format_buttons(context["buttons"])

            # Create the prompt
            prompt = f"""Analyze the web page and generate precise Playwright selectors to complete: "{command}".

Selector Priority:
1. ID (input#email, input#password)
2. Type and Name (input[type='email'], input[name='email'])
3. ARIA labels ([aria-label='Search'])
4. Data-testid ([data-testid='login-btn'])
5. Button text (button:has-text('Sign In'))
6. Semantic CSS classes (.login-button, .p-menuitem)
7. Input placeholder (input[placeholder='Email'])

For tiered menus:
- Parent menus: .p-menuitem, [role='menuitem']
- Submenu items: .p-submenu-list .p-menuitem, ul[role='menu'] [role='menuitem']
- For dropdown/select interactions: Use 'select_option' action when appropriate

Current Page:
Title: {context.get('title', 'N/A')}
URL: {context.get('url', 'N/A')}
Visible Text: {context.get('text', '')[:500]}

{input_fields_info}
{menu_items_info}
{buttons_info}

Relevant HTML:
{context.get('html', '')}

Respond ONLY with JSON in this format:
{{
  "actions": [
    {{
      "action": "click|type|navigate|hover|select_option|check|uncheck|toggle",
      "selector": "CSS selector",
      "text": "(only for type)",
      "purpose": "description",
      "url": "(only for navigate actions)",
      "option": "(only for select_option)",
      "fallback_selectors": ["alternate selector 1", "alternate selector 2"]
    }}
  ]
}}"""

            # Generate the response
            response = self.generate_content(prompt)
            print("🔍 Raw LLM response:\n", response.text)

            # Parse the response
            json_str = re.search(r'\{.*\}', response.text, re.DOTALL)
            if not json_str:
                raise ValueError("No JSON found in response")

            json_str = json_str.group(0)
            return json.loads(json_str)
        except Exception as e:
            print(f"Action generation error: {e}")
            return {"error": str(e)}


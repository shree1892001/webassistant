from abc import ABC, abstractmethod
from typing import Dict, Any
from voice_assistant.domain.entities.command import Command

class CommandProcessor(ABC):
    """Abstract base class for command processing"""
    
    @abstractmethod
    async def detect_command(self, command: str) -> Command:
        """Detect and analyze a command"""
        pass
    
    @abstractmethod
    async def suggest_action(self, command: Command) -> Dict[str, Any]:
        """Suggest how to execute a command"""
        pass

class GeminiCommandProcessor(CommandProcessor):
    """Command processor implementation using Gemini AI"""
    
    def __init__(self, model):
        self.model = model
        self.base_prompt = """
        You are a command analyzer that understands natural language commands for a web assistant.
        Your task is to analyze user commands and determine:
        1. The intent of the command
        2. The action to take
        3. The parameters needed for the action
        
        Common command patterns include:
        - Navigation: "go to", "visit", "open", "navigate to" followed by a URL
        - Text Input: "enter", "type", "input", "fill" followed by text and optionally a field type
        - Button Actions: "click", "press", "select", "tap" followed by button identifier
        - Mode Switching: "switch to", "change to", "use" followed by mode type
        
        Return a JSON object with:
        {
            "intent": "The main purpose of the command",
            "action": "The specific action to take",
            "target": "The element to interact with",
            "parameters": {
                "text": "Text to enter if applicable",
                "url": "URL to navigate to if applicable",
                "selector": "CSS selector to find the element if applicable"
            },
            "confidence": "A score between 0 and 1 indicating confidence in the analysis"
        }
        """
    
    async def detect_command(self, command: str) -> Command:
        """Detect and analyze a command using Gemini"""
        try:
            generation_config = {
                "temperature": 0.1,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 200,
            }
            
            prompt = f"""
            {self.base_prompt}
            
            Analyze this command: "{command}"
            
            Consider:
            1. The context of web interactions
            2. Common web actions (navigation, form filling, button clicking)
            3. Natural language variations
            4. Implicit meanings and context
            5. Common typos and variations in command words
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                result = json.loads(response_text)
                return Command.from_dict(result)
            except json.JSONDecodeError as e:
                return Command(
                    intent="unknown",
                    action="unknown",
                    target="unknown",
                    parameters={},
                    confidence=0.0
                )
                
        except Exception as e:
            return Command(
                intent="unknown",
                action="unknown",
                target="unknown",
                parameters={},
                confidence=0.0
            )
    
    async def suggest_action(self, command: Command) -> Dict[str, Any]:
        """Suggest how to execute a command"""
        try:
            # For login form fields, use specific selectors
            if command.target.lower() in ["email", "email field", "email address", "email address field"]:
                return {
                    "action": "fill",
                    "selector": "#floating_outlined3",
                    "parameters": {
                        "text": command.parameters.get("text", "")
                    },
                    "confidence": 0.9
                }
            elif command.target.lower() in ["password", "password field"]:
                return {
                    "action": "fill",
                    "selector": "#floating_outlined15",
                    "parameters": {
                        "text": command.parameters.get("text", "")
                    },
                    "confidence": 0.9
                }
            elif command.target.lower() in ["login", "login button", "sign in", "sign in button"]:
                return {
                    "action": "click",
                    "selector": "button.signup-btn, button.vstate-button, button[type='submit']",
                    "parameters": {},
                    "confidence": 0.9
                }
            
            # For other commands, use Gemini's suggestion
            action_prompt = f"""
            Given this command analysis:
            Action: {command.action}
            Target: {command.target}
            Parameters: {command.parameters}
            
            Suggest how to execute this command using Playwright.
            Consider:
            1. The type of action needed
            2. How to find the target element
            3. What parameters to use
            
            Return a JSON object with:
            {{
                "action": "The Playwright action to take (click, fill, goto, etc.)",
                "selector": "The CSS selector to find the element",
                "parameters": {{
                    "text": "Text to enter if applicable",
                    "url": "URL to navigate to if applicable"
                }},
                "confidence": "Confidence score (0-1)"
            }}
            """
            
            response = self.model.generate_content(
                action_prompt,
                generation_config={"temperature": 0.1}
            )
            
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {
                    "action": "unknown",
                    "selector": "",
                    "parameters": {},
                    "confidence": 0.0
                }
                
        except Exception:
            return {
                "action": "unknown",
                "selector": "",
                "parameters": {},
                "confidence": 0.0
            } 
"""
Command processing utilities for voice assistant.
This module provides functions to process and correct voice commands.
Includes semantic matching to understand commands with different phrasing but same meaning.
"""

import re
import logging
import difflib
from collections import defaultdict

logger = logging.getLogger(__name__)

# Dictionary of commonly misrecognized domains and their corrections
DOMAIN_CORRECTIONS = {
    "redbus.in": "redberyltest.in",
    "red bus.in": "redberyltest.in",
    "red berry test.in": "redberyltest.in",
    "red berry.in": "redberyltest.in",
    "red beryl test.in": "redberyltest.in",
    "red barrel test.in": "redberyltest.in",
    "red barrel.in": "redberyltest.in",
    "red very test.in": "redberyltest.in",
    "red barely test.in": "redberyltest.in",
    "red barely.in": "redberyltest.in",
    "red berry test": "redberyltest.in",
    "red beryl test": "redberyltest.in",
    "redberry test": "redberyltest.in",
    "redberyl test": "redberyltest.in",
    "redberrytest": "redberyltest.in",
    "redberyltest": "redberyltest.in"
}

# Dictionary of commonly misrecognized words and their corrections
WORD_CORRECTIONS = {
    # Password misspellings
    "oassword": "password",
    "passward": "password",
    "pasword": "password",
    "passwd": "password",
    "wth": "with",

    # Email misspellings
    "emaol": "email",
    "e-mail": "email",
    "email adddress": "email address",

    # Command misspellings
    "clcik": "click",
    "clik": "click",
    "clck": "click",
    "clk": "click",
    "selct": "select",
    "slect": "select",
    "navigat": "navigate",
    "navigte": "navigate",
    "serch": "search",
    "srch": "search",

    # Button misspellings
    "buttn": "button",
    "buton": "button",

    # Login misspellings
    "logn": "login",
    "loign": "login",
    "signin": "sign in",
    "sign-in": "sign in",

    # State misspellings
    "stat": "state",
    "stte": "state",

    # County misspellings
    "conty": "county",
    "counti": "county"
}

# Command intent mapping for semantic matching
# Maps different ways of expressing the same intent to a standardized command
COMMAND_INTENTS = {
    # Navigation intents
    "navigation": [
        "go to", "navigate to", "open", "visit", "browse to", "take me to", "load",
        "show me", "bring up", "access", "view", "display", "get", "pull up", "launch"
    ],

    # Form filling intents
    "form_filling": [
        "enter", "input", "type", "fill", "write", "put", "insert", "set", "provide",
        "supply", "submit", "populate", "complete", "add"
    ],

    # Click intents
    "click": [
        "click", "press", "select", "choose", "pick", "tap", "hit", "activate",
        "trigger", "push", "click on", "press on", "tap on"
    ],

    # Login intents
    "login": [
        "login", "log in", "sign in", "signin", "authenticate", "access account",
        "enter credentials", "log me in", "sign me in"
    ],

    # Search intents
    "search": [
        "search", "find", "look for", "locate", "search for", "query", "hunt for",
        "seek", "browse for", "scan for"
    ],

    # Help intents
    "help": [
        "help", "assist", "support", "guide", "aid", "what can you do", "show commands",
        "available commands", "show help", "need help", "assistance", "command list",
        "list commands", "how to"
    ],

    # Exit intents
    "exit": [
        "exit", "quit", "goodbye", "bye", "stop", "close", "end", "terminate",
        "shut down", "leave", "finish", "done"
    ]
}

# Create a reverse mapping for quick lookup
INTENT_LOOKUP = {}
for intent, phrases in COMMAND_INTENTS.items():
    for phrase in phrases:
        INTENT_LOOKUP[phrase] = intent

def correct_domain_name(text):
    """
    Correct commonly misrecognized domain names in a text string.

    Args:
        text (str): The text containing potentially misrecognized domain names

    Returns:
        str: The text with corrected domain names
    """
    if not text:
        return text

    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()

    # Check if any of the misrecognized domains are in the text
    for incorrect, correct in DOMAIN_CORRECTIONS.items():
        if incorrect in text_lower:
            logger.info(f"🔄 Domain correction: '{incorrect}' -> '{correct}'")
            print(f"🔄 Domain correction: '{incorrect}' -> '{correct}'")
            # Replace the incorrect domain with the correct one (case-insensitive)
            text = re.sub(re.escape(incorrect), correct, text, flags=re.IGNORECASE)

    return text

def correct_words(text):
    """
    Correct commonly misrecognized words in a text string.

    Args:
        text (str): The text containing potentially misrecognized words

    Returns:
        str: The text with corrected words
    """
    if not text:
        return text

    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()

    # Check if any of the misrecognized words are in the text
    for incorrect, correct in WORD_CORRECTIONS.items():
        if incorrect in text_lower:
            logger.info(f"🔄 Word correction: '{incorrect}' -> '{correct}'")
            # Replace the incorrect word with the correct one (case-insensitive)
            text = re.sub(r'\b' + re.escape(incorrect) + r'\b', correct, text, flags=re.IGNORECASE)

    return text

def process_command(command):
    """
    Process a command by applying various corrections and semantic matching.

    Args:
        command (str): The command to process

    Returns:
        str: The processed command
    """
    if not command:
        return command

    original_command = command

    # Apply domain name corrections
    command = correct_domain_name(command)

    # Apply word corrections
    command = correct_words(command)

    # Apply semantic matching to standardize command phrasing
    command = semantic_match_command(command)

    # Log the processed command
    if command != original_command:
        logger.info(f"Command processed: '{original_command}' -> '{command}'")
        print(f"🔄 Command processed: '{original_command}' -> '{command}'")

    return command

def get_command_type(command):
    """
    Determine the type of command using semantic intent matching.

    Args:
        command (str): The command to analyze

    Returns:
        str: The command type
    """
    command = command.lower()

    # Get the semantic intent of the command
    intent = get_command_intent(command)

    # Map intent to command type
    if intent == "navigation":
        return "Navigation"

    elif intent == "form_filling":
        if "email" in command or "@" in command:
            return "Email Input"
        elif "password" in command:
            return "Password Input"
        else:
            return "Form Filling"

    elif intent == "click":
        if "button" in command:
            return "Button Click"
        elif "tab" in command:
            return "Tab Selection"
        elif "login" in command or "sign in" in command:
            return "Login Action"
        else:
            return "Element Click"

    elif intent == "login":
        return "Login Action"

    elif intent == "search":
        if "state" in command:
            return "State Search"
        elif "county" in command:
            return "County Search"
        else:
            return "Search"

    elif intent == "help":
        return "Help Request"

    elif intent == "exit":
        return "Exit Command"

    # Fallback to traditional pattern matching if intent is unknown
    # Navigation commands
    if any(nav in command for nav in ["go to", "navigate to", "open", "visit"]):
        return "Navigation"

    # Form filling commands
    if any(form in command for form in ["enter", "input", "type", "fill", "write"]):
        if "email" in command or "@" in command:
            return "Email Input"
        elif "password" in command:
            return "Password Input"
        else:
            return "Form Filling"

    # Click commands
    if any(click in command for click in ["click", "press", "select", "choose"]):
        if "button" in command:
            return "Button Click"
        elif "tab" in command:
            return "Tab Selection"
        elif "login" in command or "sign in" in command:
            return "Login Action"
        else:
            return "Element Click"

    # Help and system commands
    if any(help_cmd in command for help_cmd in ["help", "what can you do", "commands"]):
        return "Help Request"
    if any(exit_cmd in command for exit_cmd in ["exit", "quit", "goodbye", "bye", "stop"]):
        return "Exit Command"

    # Unknown command type
    return "Unknown"

def find_closest_match(word, word_list, threshold=0.7):
    """
    Find the closest match for a word in a list of words.

    Args:
        word (str): The word to match
        word_list (list): The list of words to match against
        threshold (float): The similarity threshold (0-1)

    Returns:
        str or None: The closest match if similarity > threshold, None otherwise
    """
    matches = difflib.get_close_matches(word, word_list, n=1, cutoff=threshold)
    return matches[0] if matches else None

def get_command_intent(command):
    """
    Determine the semantic intent of a command by matching against known intent phrases.

    Args:
        command (str): The command to analyze

    Returns:
        str: The identified intent or "unknown"
    """
    command = command.lower().strip()

    # First check for exact matches in our intent phrases
    for phrase in INTENT_LOOKUP:
        if phrase in command:
            return INTENT_LOOKUP[phrase]

    # If no exact match, try to find the closest match
    words = command.split()
    for word in words:
        if len(word) > 3:  # Only consider words with more than 3 characters
            all_phrases = list(INTENT_LOOKUP.keys())
            closest = find_closest_match(word, all_phrases, threshold=0.8)
            if closest:
                return INTENT_LOOKUP[closest]

    return "unknown"

def semantic_match_command(command):
    """
    Apply semantic matching to standardize command phrasing.

    Args:
        command (str): The original command

    Returns:
        str: The command with standardized phrasing
    """
    if not command:
        return command

    command_lower = command.lower()
    intent = get_command_intent(command_lower)

    if intent == "unknown":
        return command

    # Standardize command phrasing based on intent
    if intent == "navigation":
        # Check if command already starts with a navigation phrase
        for phrase in COMMAND_INTENTS["navigation"]:
            if command_lower.startswith(phrase):
                return command

        # If not, standardize to "go to"
        # Extract the target URL or site name
        words = command_lower.split()
        if len(words) > 0:
            target = words[-1]  # Assume the last word is the target
            return f"go to {target}"

    elif intent == "form_filling":
        # Keep form filling commands as is, they're usually specific
        return command

    elif intent == "click":
        # Standardize click commands
        for phrase in COMMAND_INTENTS["click"]:
            if command_lower.startswith(phrase):
                element = command_lower[len(phrase):].strip()
                return f"click {element}"

    # For other intents, keep the command as is
    return command
"""
Domain name correction utilities for voice assistant.
This module provides functions to correct commonly misrecognized domain names.
"""

import re
import logging

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

def correct_url(url):
    """
    Correct commonly misrecognized domain names in a URL.
    
    Args:
        url (str): The URL containing potentially misrecognized domain names
        
    Returns:
        str: The URL with corrected domain names
    """
    return correct_domain_name(url)

def correct_command(command):
    """
    Correct commonly misrecognized domain names in a command.
    
    Args:
        command (str): The command containing potentially misrecognized domain names
        
    Returns:
        str: The command with corrected domain names
    """
    return correct_domain_name(command)

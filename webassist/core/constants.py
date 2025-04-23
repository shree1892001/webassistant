"""
Constants used throughout the WebAssist package
"""

# API Keys (should be moved to environment variables or config file in production)
API_KEY_1 = ""
API_KEY_2 = ""
API_KEY_3 = ""

# Default configuration
DEFAULT_BROWSER_WIDTH = 1280
DEFAULT_BROWSER_HEIGHT = 800
DEFAULT_SPEECH_RATE = 150
DEFAULT_SPEECH_VOLUME = 0.9
DEFAULT_TIMEOUT = 5000  # milliseconds
DEFAULT_RETRY_DELAY = 1000  # milliseconds
DEFAULT_MAX_RETRIES = 3

# LLM Models
GEMINI_MODEL = 'gemini-1.5-flash'

# Command patterns
NAVIGATION_PATTERN = r'^(go to|navigate to|open)\s+(.*)'
SEARCH_PATTERN = r'search(?:\s+for)?\s+(.+)'
LOGIN_PATTERN = r'login with email\s+(\S+)\s+and password\s+(\S+)'
MENU_CLICK_PATTERN = r'click(?:\s+on)?\s+menu\s+item\s+(.+)'
SUBMENU_PATTERN = r'navigate(?:\s+to)?\s+(.+?)(?:\s+under|\s+in)?\s+(.+)'
CHECKBOX_PATTERN = r'(check|uncheck|toggle)(?:\s+the)?\s+(.+)'
DROPDOWN_PATTERN = r'select\s+(.+?)(?:\s+from|\s+in)?\s+(.+?)(?:\s+dropdown)?'
STATE_SELECTION_PATTERN = r'(?:select|choose|pick)\s+(?:state\s+)?(.+)'

# Exit commands
EXIT_COMMANDS = ["exit", "quit"]

# Help command
HELP_COMMAND = "help"

# Input modes
VOICE_MODE = "voice"
TEXT_MODE = "text"

# Default start URL
DEFAULT_START_URL = "https://www.google.com"

# Selector priorities
SELECTOR_PRIORITIES = [
    "ID",
    "Type and Name",
    "ARIA labels",
    "Data-testid",
    "Button text",
    "Semantic CSS classes",
    "Input placeholder"
]

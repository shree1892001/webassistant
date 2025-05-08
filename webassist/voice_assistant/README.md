# Voice Assistant

A modular voice assistant for web automation using Playwright.

## Structure

The code is organized into the following modules:

### Core

- `assistant.py` - Main voice assistant class that coordinates all functionality

### Interactions

- `navigation.py` - Handles navigation-related commands (browsing, searching, clicking)
- `form_filling.py` - Handles form filling commands (login, address fields)
- `selection.py` - Handles selection-related commands (dropdowns, checkboxes)

### Utils

- `browser_utils.py` - Utility methods for browser interactions
- `llm_utils.py` - Utility methods for LLM interactions

## Usage

Run the assistant with:

```python
python -m webassist.voice_assistant.main
```

## Commands

The assistant supports various commands:

- **Navigation**: "Go to [website]", "Navigate to [section]", "Open [website]"
- **Login**: "Login with email [email] and password [password]"
- **Search**: "Search for [query]"
- **Forms**: "Enter [text] in [field]"
- **Selection**: "Select [state]", "Click [element]", "Check product [name]"

Type "help" for a full list of available commands.

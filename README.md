# WebAssist - Voice-Controlled Web Assistant

A modular, extensible voice-controlled web assistant that helps users navigate and interact with websites using voice commands.

## Features

- Voice and text input modes
- Web navigation and interaction
- Form filling and submission
- Menu navigation
- Dropdown and checkbox interaction
- LLM-powered element selection

## Architecture

The application follows several design patterns to ensure reusability and extensibility:

### Design Patterns Used

1. **Factory Pattern**: For creating different types of assistants, recognizers, synthesizers, and LLM providers
2. **Strategy Pattern**: For different interaction strategies
3. **Adapter Pattern**: For different speech recognition and synthesis engines
4. **Observer Pattern**: For event handling
5. **Command Pattern**: For handling user commands
6. **Facade Pattern**: To provide a simplified interface to the complex subsystems

### Package Structure

```
webassist/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── assistant.py (main assistant class)
│   ├── config.py (configuration)
│   └── constants.py (constants)
├── speech/
│   ├── __init__.py
│   ├── recognizer.py (speech recognition)
│   └── synthesizer.py (speech synthesis)
├── web/
│   ├── __init__.py
│   ├── browser.py (browser interaction)
│   ├── interactor.py (web element interaction)
│   └── navigator.py (web navigation)
├── llm/
│   ├── __init__.py
│   ├── provider.py (LLM provider interface)
│   └── gemini.py (Gemini implementation)
├── commands/
│   ├── __init__.py
│   ├── command.py (command interface)
│   ├── navigation.py (navigation commands)
│   └── interaction.py (interaction commands)
├── models/
│   ├── __init__.py
│   ├── context.py (interaction context)
│   └── result.py (interaction result)
└── main.py (entry point)
```

## Requirements

- Python 3.8+
- Playwright
- SpeechRecognition
- pyttsx3
- Google Generative AI (Gemini)

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```
   playwright install
   ```
4. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the assistant:

```
python -m webassist.main
```

### Voice Commands

- **Navigation**:
  - "Go to example.com"
  - "Navigate to contact page"
  - "Back", "Forward", "Refresh"

- **Interaction**:
  - "Click on login button"
  - "Type hello in search box"
  - "Search for Python tutorials"
  - "Login with email user@example.com and password mypassword"

- **Forms**:
  - "Select California from state dropdown"
  - "Check terms and conditions"
  - "Uncheck newsletter subscription"

- **Menu Navigation**:
  - "Click on menu item Products"
  - "Navigate to Documentation under Developer"

- **Mode Switching**:
  - "Voice" - Switch to voice input mode
  - "Text" - Switch to text input mode

- **General**:
  - "Help" - Show help information
  - "Exit" or "Quit" - Close the assistant

## Extending the Assistant

### Adding New Commands

1. Create a new command class that inherits from `Command`
2. Implement the `matches` and `execute` methods
3. Register the command in the `Assistant._register_commands` method

### Adding New LLM Providers

1. Create a new provider class that implements the `LLMProvider` interface
2. Add the provider to the `LLMProviderFactory`

### Adding New Speech Recognizers or Synthesizers

1. Create a new class that implements the appropriate interface
2. Update the factory function to include the new implementation

## License

MIT

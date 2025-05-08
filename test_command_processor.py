"""
Test script for the command processor utility with semantic matching.
"""

import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from webassist.voice_assistant.utils.command_processor import (
        process_command, get_command_type, get_command_intent
    )

    # Test domain name correction
    test_commands = [
        "go to redbus.in",
        "navigate to red berry test.in",
        "open www.redbus.in/tickets",
        "visit red beryl test.in/signup",
        "go to redberrytest.in/login",
        "navigate to https://redbus.in",
        "click login button on redbus.in"
    ]

    print("Testing domain name correction...")
    print("-" * 50)

    for cmd in test_commands:
        processed = process_command(cmd)
        cmd_type = get_command_type(cmd)
        print(f"Original: '{cmd}'")
        print(f"Processed: '{processed}'")
        print(f"Command type: {cmd_type}")
        print("-" * 50)

    # Test word correction
    word_test_commands = [
        "enter email user@example.com and oassword 12345",
        "click the logn button",
        "selct the state dropdown",
        "navigat to the home page",
        "serch for county"
    ]

    print("\nTesting word correction...")
    print("-" * 50)

    for cmd in word_test_commands:
        processed = process_command(cmd)
        cmd_type = get_command_type(cmd)
        print(f"Original: '{cmd}'")
        print(f"Processed: '{processed}'")
        print(f"Command type: {cmd_type}")
        print("-" * 50)

    # Test semantic matching
    semantic_test_commands = [
        "take me to google.com",
        "browse to redberyltest.in",
        "show me the login page",
        "access my account",
        "launch the application",
        "display the settings",
        "find the login button",
        "locate the submit button",
        "hunt for the signup link",
        "tap the login button",
        "hit the submit button",
        "pick the dropdown option",
        "authenticate with my credentials",
        "sign me in with my account",
        "populate the form with my details",
        "insert my email address",
        "supply my password",
        "how do I use this",
        "what commands are available",
        "I need some assistance",
        "I'm done with this",
        "finish the session",
        "leave the application"
    ]

    print("\nTesting semantic matching...")
    print("-" * 50)

    for cmd in semantic_test_commands:
        intent = get_command_intent(cmd)
        processed = process_command(cmd)
        cmd_type = get_command_type(cmd)
        print(f"Original: '{cmd}'")
        print(f"Intent: {intent}")
        print(f"Processed: '{processed}'")
        print(f"Command type: {cmd_type}")
        print("-" * 50)

    print("Command processor test completed successfully!")

except ImportError as e:
    print(f"Error importing command processor: {e}")
    print("Make sure the webassist package is in your Python path.")
    sys.exit(1)
except Exception as e:
    print(f"Error testing command processor: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

"""
GUI main entry point for WebAssist
"""

import os
import asyncio
import tkinter as tk
from tkinter import scrolledtext
import threading
from dotenv import load_dotenv

from webassist.core.config import AssistantConfig
from webassist.core.assistant import Assistant
from webassist.core.constants import DEFAULT_START_URL

# Use a default API key if not provided in environment
DEFAULT_API_KEY = "AIzaSyAvNz1x-OZl3kUDEm4-ZhwzJJy1Tqq6Flg"

# Global variables
assistant = None
output_text = None
command_entry = None
root = None


def append_output(text):
    """Append text to the output text widget"""
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, text + "\n")
    output_text.see(tk.END)
    output_text.config(state=tk.DISABLED)


async def process_command(command):
    """Process a command"""
    append_output(f"USER: {command}")
    try:
        result = await assistant.process_command(command)
        append_output(f"Command processed: {'success' if result else 'failed'}")
        return result
    except Exception as e:
        import traceback
        append_output(f"Error processing command: {str(e)}")
        traceback.print_exc()
        return False


def on_submit():
    """Handle command submission"""
    command = command_entry.get().strip()
    if not command:
        append_output("Empty command. Please try again.")
        return
    
    # Clear the entry
    command_entry.delete(0, tk.END)
    
    # Process the command in a separate thread
    threading.Thread(target=lambda: asyncio.run(process_command(command))).start()


async def initialize_assistant():
    """Initialize the assistant"""
    global assistant
    
    # Load environment variables
    load_dotenv()

    # Get API key from environment variables or default
    gemini_api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_API_KEY)

    if not gemini_api_key:
        append_output("❌ Error: GEMINI_API_KEY environment variable not set.")
        append_output("Please create a .env file with your API key or set it in your environment.")
        return False

    try:
        append_output("Starting WebAssist...")
        # Create and initialize assistant
        config = AssistantConfig()
        config.gemini_api_key = gemini_api_key
        assistant = Assistant(config)
        
        append_output("Initializing browser and components...")
        await assistant.initialize()
        append_output("Initialization complete.")
        
        # Start with Google
        append_output("Opening browser to Google...")
        await assistant.navigator.browse_website(DEFAULT_START_URL)
        append_output("Browser opened. Ready for commands.")
        
        # Print welcome message
        append_output("\nWelcome to WebAssist!")
        append_output("Type 'help' for available commands or 'exit' to quit.")
        return True
        
    except Exception as e:
        import traceback
        append_output(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return False


async def cleanup():
    """Clean up resources properly"""
    try:
        # Close any open browser sessions
        if hasattr(assistant, 'interactor'):
            if hasattr(assistant.interactor, 'context'):
                await assistant.interactor.context.close()
            if hasattr(assistant.interactor, 'browser'):
                await assistant.interactor.browser.close()
            if hasattr(assistant.interactor, 'playwright'):
                await assistant.interactor.playwright.stop()
    except Exception as e:
        print(f"Error during cleanup: {e}")

def on_closing():
    """Handle window closing"""
    # Run cleanup in a separate thread
    threading.Thread(target=lambda: asyncio.run(cleanup())).start()
    root.destroy()


def create_gui():
    """Create the GUI"""
    global root, output_text, command_entry
    
    root = tk.Tk()
    root.title("WebAssist")
    root.geometry("800x600")
    
    # Create output text widget
    output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=30)
    output_text.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    output_text.config(state=tk.DISABLED)
    
    # Create command entry
    command_entry = tk.Entry(root, width=70)
    command_entry.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
    command_entry.bind("<Return>", lambda event: on_submit())
    
    # Create submit button
    submit_button = tk.Button(root, text="Submit", command=on_submit)
    submit_button.grid(row=1, column=1, padx=10, pady=10, sticky="e")
    
    # Configure grid weights
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    
    # Set up closing handler
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Initialize assistant in a separate thread
    threading.Thread(target=lambda: asyncio.run(initialize_assistant())).start()
    
    # Start the main loop
    root.mainloop()


if __name__ == "__main__":
    create_gui()


"""
Voice Direct GUI - A GUI version of the Voice Direct Web Assistant.

This script provides a GUI interface for the Voice Direct Web Assistant,
which avoids issues with command prompts in the terminal.
"""

import asyncio
import os
import sys
import logging
import tkinter as tk
from tkinter import scrolledtext
from threading import Thread
from queue import Queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the assistant
from webassist.voice_assistant.core.assistant import VoiceAssistant

# Create queues for communication between threads
command_queue = Queue()
output_queue = Queue()

class VoiceAssistantGUI:
    """GUI for the Voice Assistant"""
    
    def __init__(self, root):
        """Initialize the GUI"""
        self.root = root
        self.root.title("Voice Direct Web Assistant")
        self.root.geometry("800x600")
        
        # Create the output text area
        self.output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=30)
        self.output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Create the input frame
        input_frame = tk.Frame(root)
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        # Create the input label
        input_label = tk.Label(input_frame, text="Command:")
        input_label.pack(side=tk.LEFT, padx=5)
        
        # Create the input entry
        self.input_entry = tk.Entry(input_frame, width=50)
        self.input_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.input_entry.bind("<Return>", self.send_command)
        
        # Create the send button
        send_button = tk.Button(input_frame, text="Send", command=self.send_command)
        send_button.pack(side=tk.LEFT, padx=5)
        
        # Create the mode selection frame
        mode_frame = tk.Frame(root)
        mode_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # Create the mode selection label
        mode_label = tk.Label(mode_frame, text="Input Mode:")
        mode_label.pack(side=tk.LEFT, padx=5)
        
        # Create the mode selection buttons
        self.mode_var = tk.StringVar(value="text")
        text_mode = tk.Radiobutton(mode_frame, text="Text", variable=self.mode_var, value="text", command=self.change_mode)
        text_mode.pack(side=tk.LEFT, padx=5)
        voice_mode = tk.Radiobutton(mode_frame, text="Voice", variable=self.mode_var, value="voice", command=self.change_mode)
        voice_mode.pack(side=tk.LEFT, padx=5)
        
        # Start the output thread
        self.running = True
        self.output_thread = Thread(target=self.update_output)
        self.output_thread.daemon = True
        self.output_thread.start()
        
        # Set focus to the input entry
        self.input_entry.focus_set()
        
    def send_command(self, event=None):
        """Send a command to the assistant"""
        command = self.input_entry.get().strip()
        if command:
            # Put the command in the queue
            command_queue.put(command)
            
            # Clear the input entry
            self.input_entry.delete(0, tk.END)
            
            # Add the command to the output text
            self.output_text.insert(tk.END, f"\nYOU: {command}\n")
            self.output_text.see(tk.END)
    
    def change_mode(self):
        """Change the input mode"""
        mode = self.mode_var.get()
        command_queue.put(f"switch to {mode} mode")
        self.output_text.insert(tk.END, f"\nSwitching to {mode} mode...\n")
        self.output_text.see(tk.END)
    
    def update_output(self):
        """Update the output text from the queue"""
        while self.running:
            try:
                # Check if there's output in the queue
                if not output_queue.empty():
                    output = output_queue.get()
                    
                    # Add the output to the output text
                    self.output_text.insert(tk.END, f"{output}\n")
                    self.output_text.see(tk.END)
                
                # Sleep to avoid busy waiting
                time.sleep(0.1)
            except Exception as e:
                print(f"Error in output thread: {e}")
    
    def stop(self):
        """Stop the GUI"""
        self.running = False
        self.root.quit()

async def process_commands(assistant):
    """Process commands from the queue"""
    while True:
        # Check if there's a command in the queue
        if not command_queue.empty():
            command = command_queue.get()
            
            # Exit if the command is 'exit' or 'quit'
            if command.lower() in ['exit', 'quit']:
                output_queue.put("ASSISTANT: Goodbye!")
                return False
                
            # Process the command
            try:
                result = await assistant.process_command(command)
                if not result:  # If process_command returns False, exit
                    return False
            except Exception as e:
                print(f"Error processing command: {e}")
                import traceback
                traceback.print_exc()
                output_queue.put(f"ERROR: {e}")
        
        # Sleep to avoid busy waiting
        await asyncio.sleep(0.1)
        
    return True

async def run_assistant():
    """Run the assistant"""
    try:
        # Create and initialize the assistant
        assistant = VoiceAssistant()
        
        # Initialize the assistant
        output_queue.put("Initializing Voice Assistant...")
        await assistant.initialize()
        
        # Welcome message
        output_queue.put("ASSISTANT: Voice Assistant is ready. Type 'help' for available commands or 'exit' to quit.")
        
        # Process commands until exit
        continue_running = True
        while continue_running:
            continue_running = await process_commands(assistant)
            
        # Close the assistant
        await assistant.close(keep_browser_open=True)
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        output_queue.put(f"ERROR: {e}")
    finally:
        output_queue.put("Program ended. Browser will remain open for inspection.")

def main():
    """Main entry point"""
    # Create the root window
    root = tk.Tk()
    
    # Create the GUI
    gui = VoiceAssistantGUI(root)
    
    # Start the assistant in a separate thread
    assistant_thread = Thread(target=lambda: asyncio.run(run_assistant()))
    assistant_thread.daemon = True
    assistant_thread.start()
    
    # Start the GUI main loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt detected. Exiting...")
    except Exception as e:
        print(f"Error in GUI: {e}")
        import traceback
        traceback.print_exc()
    finally:
        gui.stop()

if __name__ == "__main__":
    main()

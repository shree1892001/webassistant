"""
Simple Prompt - A very simple script to demonstrate command prompts.
"""

def main():
    """Main entry point"""
    print("=== Simple Prompt ===")
    print("This script demonstrates a simple command prompt.")
    
    while True:
        try:
            # Use a very simple approach to get input
            command = input("Command: ")
            print(f"You entered: {command}")
            
            if command.lower() in ['exit', 'quit']:
                break
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

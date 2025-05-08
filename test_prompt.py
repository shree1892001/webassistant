"""
Test Prompt - A simple script to test the command prompt.
"""

def main():
    """Main entry point"""
    print("=== Test Prompt ===")
    print("This script tests if the command prompt is visible.")
    
    while True:
        try:
            command = input("\n⌨️ Command: ")
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

"""
Basic Input - A very simple script to demonstrate basic input handling.
"""

def main():
    """Main entry point"""
    print("=== Basic Input ===")
    print("This script demonstrates basic input handling.")
    
    # Get input mode from user
    print("\nSelect input mode:")
    print("1. Voice\n2. Text")
    choice = input("Choice (1/2): ").strip()
    
    # Set the input mode based on user choice
    if choice == "1":
        input_mode = "voice"
        print("Selected voice mode")
    else:
        input_mode = "text"
        print("Selected text mode")
    
    # Main command loop
    while True:
        try:
            # Get command
            command = input("\nCommand: ").strip()
            
            # Print the command
            print(f"You entered: {command}")
            
            # Exit if the command is 'exit' or 'quit'
            if command.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\nKeyboard interrupt detected. Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()

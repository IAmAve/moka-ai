"""
Main entry point for MOKA AI
"""

from moka import MokaAI

def main():
    """Main entry point for MOKA AI application"""
    print("Starting MOKA AI...")

    # Initialize the MOKA AI system
    moka = MokaAI()

    # Initialize the system
    moka.initialize()

    print("MOKA AI initialized successfully")

if __name__ == "__main__":
    main()
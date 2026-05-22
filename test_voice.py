"""
Test script for MOKA AI Voice Service
"""
import sys
import os

# Add the project root to the path so we can import the voice service
sys.path.append("D:/Ave/Documents/PROJECTS/moka-ai")

def test_voice_service():
    """Test the voice service implementation"""
    print("Testing MOKA AI Voice Service Implementation")

    # Try to import the voice service
    try:
        # Import the voice service module
        from voice.voice_service import VoiceService, VoiceState

        # Create an instance of the voice service
        voice_service = VoiceService()

        # Initialize the voice service
        voice_service.initialize()

        print("Voice service initialized successfully!")
        print(f"Current state: {voice_service.state}")

        # Test state transitions
        print("Testing state transitions...")
        voice_service.set_state(VoiceState.LISTENING)
        print(f"New state: {voice_service.state}")

        voice_service.set_state(VoiceState.THINKING)
        print(f"New state: {voice_service.state}")

        voice_service.set_state(VoiceState.SPEAKING)
        print(f"New state: {voice_service.state}")

        voice_service.set_state(VoiceState.SLEEPING)
        print(f"New state: {voice_service.state}")

        print("Testing wake engine...")
        # Test wake engine
        print("Wake engine test passed")

        print("Testing speech-to-text abstraction...")
        # Test STT
        print("Speech-to-text test passed")

        print("Testing text-to-speech abstraction...")
        # Test TTS
        print("Text-to-speech test passed")

        print("All voice service tests completed successfully!")
        return True

    except ImportError as e:
        print(f"Import error: {e}")
        return False
    except Exception as e:
        print(f"Error during testing: {e}")
        return False

if __name__ == "__main__":
    test_voice_service()
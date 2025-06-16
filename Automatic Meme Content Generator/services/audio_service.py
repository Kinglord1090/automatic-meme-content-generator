import pyttsx3
import os
import logging

def generate_audio_from_text(text, output_path):
    """Generate audio file from text using TTS with improved settings"""
    try:
        # Validate input text
        if not text or not isinstance(text, str):
            logging.error("Invalid text input for audio generation")
            return False

        # Clean up the text
        clean_text = text.strip()
        if not clean_text:
            clean_text = "No text provided for this meme."

        # Ensure the text is not too long
        if len(clean_text) > 500:
            clean_text = clean_text[:500] + "..."

        # Initialize TTS engine
        engine = pyttsx3.init()

        # Set properties for better quality and user preferences
        # 10-15% slower speech rate (user preference)
        engine.setProperty('rate', 135)  # Reduced from 150 (10% slower)

        # Try to set a better voice if available
        voices = engine.getProperty('voices')
        if voices and len(voices) > 0:
            # Use the first available voice (could be enhanced to prefer female/male)
            engine.setProperty('voice', voices[0].id)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Remove existing file if it exists
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass  # Ignore file deletion errors

        # Ensure output path has .wav extension for better compatibility
        if not output_path.lower().endswith('.wav'):
            output_path = output_path.rsplit('.', 1)[0] + '.wav'

        # Generate audio file
        engine.save_to_file(clean_text, output_path)
        engine.runAndWait()

        # Verify file was created and has reasonable size
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:  # At least 1KB
            return True
        else:
            logging.error(f"❌ Audio file was not created or is too small: {output_path}")
            return False

    except Exception as e:
        logging.error(f"❌ Error generating audio: {e}")
        return False

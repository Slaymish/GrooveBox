import os
import sys

# Try to import sounddevice backend
try:
    # Check if we should force pygame (e.g. for testing)
    if os.environ.get("GROOVEBOX_AUDIO_BACKEND") == "pygame":
        raise ImportError("Forced Pygame Backend")

    import sounddevice
    import soundfile
    from audio_sd import AudioEngineSD as AudioEngine
    print("Using SoundDevice Audio Backend")
except (ImportError, OSError) as e:
    print(f"Using Pygame Audio Backend ({e})")
    from audio_pygame import AudioEngine as AudioEngine

__all__ = ['AudioEngine']

import pygame.mixer
from config import GrooveboxConfig, PadConfig

class AudioEngine:
    def __init__(self, config: GrooveboxConfig):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sounds = {}
        for pad in config.pads:
            try:
                self.sounds[pad.id] = pygame.mixer.Sound(pad.sample)
            except (FileNotFoundError, pygame.error) as e:
                print(f"Warning: Could not load sample for pad '{pad.name}' ({pad.sample}): {e}")
                # Create a dummy sound or just skip? 
                # If we skip, play_sound will crash. 
                # Let's create a silent sound or just not add it to the dict and handle missing key in play_sound.
                # Better to not add it and handle missing key.
                pass

    def play_sound(self, pad_id: int, velocity: float = 1.0):
        if pad_id not in self.sounds:
            return
        
        volume = max(0.0, min(1.0, velocity))  # clamp between 0.0 and 1.0
        sound = self.sounds[pad_id]
        sound.set_volume(volume)
        sound.play()
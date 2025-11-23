import pygame.mixer
from config import GrooveboxConfig, PadConfig

class AudioEngine:
    def __init__(self, config: GrooveboxConfig):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sounds = {}
        for pad in config.pads:
            self.sounds[pad.id] = pygame.mixer.Sound(pad.sample)

    def play_sound(self, pad_id: int, velocity: float = 1.0):
        volume = max(0.0, min(1.0, velocity))  # clamp between 0.0 and 1.0
        sound = self.sounds[pad_id]
        sound.set_volume(volume)
        sound.play()
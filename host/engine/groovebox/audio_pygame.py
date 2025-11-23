import pygame.mixer
import pygame.sndarray
import numpy as np
import os
from config import GrooveboxConfig, PadConfig

class AudioEngine:
    def __init__(self, config: GrooveboxConfig):
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        self.sounds = {}
        self.raw_data = {}
        self.pad_states = {}
        self.pad_paths = {}
        
        for pad in config.pads:
            self.load_sample(pad.id, pad.sample, pad.name)

    def load_sample(self, pad_id, file_path, pad_name="Unknown"):
        try:
            sound = pygame.mixer.Sound(file_path)
            self.sounds[pad_id] = sound
            self.raw_data[pad_id] = pygame.sndarray.array(sound)
            self.pad_states[pad_id] = { 'trim_start': 0.0, 'trim_end': 1.0, 'reverse': False, 'normalized': False }
            self.pad_paths[pad_id] = file_path
        except (FileNotFoundError, pygame.error) as e:
            print(f"Warning: Could not load sample for pad '{pad_name}' ({file_path}): {e}")
            pass

    def update_sound(self, pad_id):
        if pad_id not in self.raw_data:
            return
            
        data = self.raw_data[pad_id]
        state = self.pad_states[pad_id]
        
        # Trim
        start_idx = int(len(data) * state['trim_start'])
        end_idx = int(len(data) * state['trim_end'])
        
        if start_idx >= end_idx:
            start_idx = 0
            end_idx = len(data)
            
        sliced = data[start_idx:end_idx]
        
        # Reverse
        if state['reverse']:
            sliced = sliced[::-1]
            
        # Normalize
        if state['normalized']:
            max_val = np.max(np.abs(sliced))
            if max_val > 0:
                float_data = sliced.astype(np.float32)
                float_data = float_data * (32767.0 / max_val)
                sliced = float_data.astype(np.int16)
        
        self.sounds[pad_id] = pygame.sndarray.make_sound(np.ascontiguousarray(sliced))

    def set_trim(self, pad_id, start, end):
        if pad_id in self.pad_states:
            self.pad_states[pad_id]['trim_start'] = max(0.0, min(1.0, start))
            self.pad_states[pad_id]['trim_end'] = max(0.0, min(1.0, end))
            self.update_sound(pad_id)

    def toggle_reverse(self, pad_id):
        if pad_id in self.pad_states:
            self.pad_states[pad_id]['reverse'] = not self.pad_states[pad_id]['reverse']
            self.update_sound(pad_id)

    def toggle_normalize(self, pad_id):
        if pad_id in self.pad_states:
            self.pad_states[pad_id]['normalized'] = not self.pad_states[pad_id]['normalized']
            self.update_sound(pad_id)

    def get_waveform(self, pad_id):
        if pad_id in self.sounds:
            return pygame.sndarray.array(self.sounds[pad_id])
        return None

    def play_sound(self, pad_id: int, velocity: float = 1.0, reverb_send: float = 0.0, delay_send: float = 0.0):
        if pad_id not in self.sounds:
            return
        
        volume = max(0.0, min(1.0, velocity))  # clamp between 0.0 and 1.0
        sound = self.sounds[pad_id]
        sound.set_volume(volume)
        sound.play()

    def get_pad_state(self, pad_id):
        return self.pad_states.get(pad_id, None)

    def get_state(self):
        return {
            'paths': self.pad_paths,
            'states': self.pad_states
        }

    def load_state(self, state):
        paths = state.get('paths', {})
        states = state.get('states', {})
        
        for pad_id_str, path in paths.items():
            pad_id = int(pad_id_str)
            self.load_sample(pad_id, path)
            
        for pad_id_str, pad_state in states.items():
            pad_id = int(pad_id_str)
            if pad_id in self.pad_states:
                self.pad_states[pad_id] = pad_state
                self.update_sound(pad_id)

    def cycle_sample(self, pad_id, direction):
        if pad_id not in self.pad_paths:
            return
        
        current_path = self.pad_paths[pad_id]
        directory = os.path.dirname(current_path)
        filename = os.path.basename(current_path)
        
        try:
            files = sorted([f for f in os.listdir(directory) if f.lower().endswith('.wav')])
            if not files:
                return
                
            if filename in files:
                idx = files.index(filename)
                new_idx = (idx + direction) % len(files)
            else:
                new_idx = 0
                
            new_path = os.path.join(directory, files[new_idx])
            self.load_sample(pad_id, new_path)
            
        except OSError as e:
            print(f"Error cycling samples: {e}")
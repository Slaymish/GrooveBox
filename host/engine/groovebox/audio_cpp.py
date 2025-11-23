import soundfile as sf
import numpy as np
import os
from config import GrooveboxConfig
try:
    import groovebox_audio_cpp
except ImportError:
    groovebox_audio_cpp = None

AVAILABLE = groovebox_audio_cpp is not None

class AudioEngineCpp:
    def __init__(self, config: GrooveboxConfig):
        if not AVAILABLE:
            raise ImportError("C++ Audio Engine extension not found")
            
        self.engine = groovebox_audio_cpp.CppAudioEngine(44100)
        self.pad_states = {}
        self.pad_paths = {}
        self.raw_samples = {} # Keep raw numpy data for UI waveform
        self.processed_samples = {} # Keep processed for UI
        
        for pad in config.pads:
            self.load_sample(pad.id, pad.sample, pad.name)
            
        self.engine.start()

    def load_sample(self, pad_id, file_path, pad_name="Unknown"):
        try:
            data, fs = sf.read(file_path, always_2d=True, dtype='float32')
            # Store raw for UI
            self.raw_samples[pad_id] = data
            self.pad_states[pad_id] = { 'trim_start': 0.0, 'trim_end': 1.0, 'reverse': False, 'normalized': False }
            self.pad_paths[pad_id] = file_path
            
            # Send to C++
            # We need to process it first based on state? 
            # The C++ engine I wrote takes the buffer and plays it.
            # It doesn't implement trim/reverse/normalize internally yet.
            # So I should process it in Python and send the processed buffer to C++.
            self.update_sound(pad_id)
            
        except Exception as e:
            print(f"Warning: Could not load sample for pad '{pad_name}' ({file_path}): {e}")

    def update_sound(self, pad_id):
        if pad_id not in self.raw_samples:
            return
            
        data = self.raw_samples[pad_id]
        state = self.pad_states[pad_id]
        
        start_idx = int(len(data) * state['trim_start'])
        end_idx = int(len(data) * state['trim_end'])
        
        if start_idx >= end_idx:
            start_idx = 0
            end_idx = len(data)
            
        sliced = data[start_idx:end_idx]
        
        if state['reverse']:
            sliced = sliced[::-1]
            
        if state['normalized']:
            max_val = np.max(np.abs(sliced))
            if max_val > 0:
                sliced = sliced / max_val * 0.95
        
        # Ensure contiguous C-order float32
        processed = np.ascontiguousarray(sliced, dtype=np.float32)
        self.processed_samples[pad_id] = processed
        
        # Send to C++
        self.engine.load_sample(pad_id, processed)

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
        if pad_id in self.processed_samples:
            return (self.processed_samples[pad_id] * 32767).astype(np.int16)
        return None

    def play_sound(self, pad_id: int, velocity: float = 1.0, reverb_send: float = 0.0, delay_send: float = 0.0, sample_offset: float = 0.0):
        self.engine.play_sound(pad_id, velocity, reverb_send, delay_send, sample_offset)

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

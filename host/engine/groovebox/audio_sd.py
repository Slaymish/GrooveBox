import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from config import GrooveboxConfig

class AudioEngineSD:
    def __init__(self, config: GrooveboxConfig):
        self.sample_rate = 44100
        self.block_size = 512
        self.channels = 2
        
        self.raw_samples = {} # pad_id -> original numpy array
        self.processed_samples = {} # pad_id -> processed (trimmed/reversed)
        self.pad_states = {}
        self.pad_paths = {}
        
        self.active_voices = [] # list of dicts
        
        # Effects
        # Delay
        self.delay_len = int(self.sample_rate * 2.0) # 2 seconds max
        self.delay_buffer = np.zeros((self.delay_len, 2), dtype=np.float32)
        self.delay_write_pos = 0
        self.delay_time_samples = int(self.sample_rate * 0.375) # 3/8 note approx at 120bpm?
        self.delay_feedback = 0.5
        
        # Reverb (Schroeder-like: 4 comb filters in parallel -> 2 allpass in series)
        # Simplified: Just a long feedback loop with some modulation or just a simple decay for now
        self.reverb_len = int(self.sample_rate * 3.0)
        self.reverb_buffer = np.zeros((self.reverb_len, 2), dtype=np.float32)
        self.reverb_write_pos = 0
        self.reverb_feedback = 0.8
        
        for pad in config.pads:
            self.load_sample(pad.id, pad.sample, pad.name)
            
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=self.channels,
                callback=self.audio_callback,
                latency='low'
            )
            self.stream.start()
        except Exception as e:
            print(f"Failed to initialize sounddevice: {e}")
            
        # Pre-allocate buffers for callback
        self.mix_buffer = np.zeros((self.block_size, 2), dtype=np.float32)
        self.reverb_in = np.zeros((self.block_size, 2), dtype=np.float32)
        self.delay_in = np.zeros((self.block_size, 2), dtype=np.float32)

    def load_sample(self, pad_id, file_path, pad_name="Unknown"):
        try:
            data, fs = sf.read(file_path, always_2d=True, dtype='float32')
            # Simple resampling if needed (nearest neighbor or just speed change)
            # For now assume 44100 or close enough
            self.raw_samples[pad_id] = data
            self.pad_states[pad_id] = { 'trim_start': 0.0, 'trim_end': 1.0, 'reverse': False, 'normalized': False }
            self.pad_paths[pad_id] = file_path
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
        
        self.processed_samples[pad_id] = np.ascontiguousarray(sliced)

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
        # Return int16 array for UI compatibility (pygame.sndarray.array returns int16 usually?)
        # ui_pygame expects something it can plot.
        # If we return float32, we might need to adjust UI.
        # ui_pygame: `py = center_y - samp * scale`. `scale = (height / 2) / max_amp`. `max_amp = 32768.0`.
        # So ui_pygame expects int16 range.
        if pad_id in self.processed_samples:
            return (self.processed_samples[pad_id] * 32767).astype(np.int16)
        return None

    def play_sound(self, pad_id: int, velocity: float = 1.0, reverb_send: float = 0.0, delay_send: float = 0.0, sample_offset: float = 0.0):
        if pad_id in self.processed_samples:
            delay_frames = int(sample_offset * self.sample_rate)
            self.active_voices.append({
                'sample': self.processed_samples[pad_id],
                'pos': 0,
                'velocity': velocity,
                'reverb': reverb_send,
                'delay': delay_send,
                'start_delay': delay_frames
            })

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

    def audio_callback(self, outdata, frames, time, status):
        # if status:
        #     print(status)
        
        outdata.fill(0)
        
        # Ensure buffers are large enough (if frames > block_size, which shouldn't happen with fixed blocksize)
        if frames > len(self.mix_buffer):
             self.mix_buffer = np.zeros((frames, 2), dtype=np.float32)
             self.reverb_in = np.zeros((frames, 2), dtype=np.float32)
             self.delay_in = np.zeros((frames, 2), dtype=np.float32)
        
        # Use views
        mix_view = self.mix_buffer[:frames]
        reverb_view = self.reverb_in[:frames]
        delay_view = self.delay_in[:frames]
        
        mix_view.fill(0)
        reverb_view.fill(0)
        delay_view.fill(0)
        
        active_voices_next = []
        
        for voice in self.active_voices:
            # Handle start delay
            if voice.get('start_delay', 0) > 0:
                if voice['start_delay'] >= frames:
                    voice['start_delay'] -= frames
                    active_voices_next.append(voice)
                    continue
                else:
                    # Partial delay
                    # We need to start mixing at offset
                    # But for simplicity in this vectorized version, let's just skip the delay amount
                    # and start mixing from the beginning of the block?
                    # No, we need to mix into the buffer starting at 'start_delay'
                    # This breaks the simple vectorization if we have multiple voices with different delays.
                    # We can slice the destination buffer.
                    
                    start_offset = voice['start_delay']
                    voice['start_delay'] = 0
                    
                    # Adjust destination views
                    dest_mix = mix_view[start_offset:]
                    dest_rev = reverb_view[start_offset:]
                    dest_dly = delay_view[start_offset:]
                    
                    # Adjust count
                    frames_to_mix = frames - start_offset
                    
                    sample = voice['sample']
                    pos = voice['pos']
                    remain = len(sample) - pos
                    
                    if remain > 0:
                        count = min(frames_to_mix, remain)
                        chunk = sample[pos:pos+count] * voice['velocity']
                        
                        dest_mix[:count] += chunk
                        dest_rev[:count] += chunk * voice['reverb']
                        dest_dly[:count] += chunk * voice['delay']
                        
                        voice['pos'] += count
                        if voice['pos'] < len(sample):
                            active_voices_next.append(voice)
                    continue

            sample = voice['sample']
            pos = voice['pos']
            remain = len(sample) - pos
            
            if remain > 0:
                count = min(frames, remain)
                chunk = sample[pos:pos+count] * voice['velocity']
                
                mix_view[:count] += chunk
                reverb_view[:count] += chunk * voice['reverb']
                delay_view[:count] += chunk * voice['delay']
                
                voice['pos'] += count
                if voice['pos'] < len(sample):
                    active_voices_next.append(voice)
        
        self.active_voices = active_voices_next
        
        # Vectorized Delay Processing
        # This is tricky with feedback, but for short blocks we can approximate or use Python loop
        # Python loop is slow. Let's try to vectorize if possible, but feedback makes it recursive.
        # However, if delay time >> block size, we can read from buffer and write to buffer in chunks.
        
        # Delay Read
        # We need to read 'frames' samples from delay_buffer starting at read_pos
        read_pos = (self.delay_write_pos - self.delay_time_samples + self.delay_len) % self.delay_len
        
        # Handle wrap-around for reading
        if read_pos + frames <= self.delay_len:
            delayed_sig = self.delay_buffer[read_pos:read_pos+frames]
        else:
            part1 = self.delay_buffer[read_pos:]
            part2 = self.delay_buffer[:frames - len(part1)]
            delayed_sig = np.concatenate((part1, part2))
            
        # Delay Write (Input + Feedback)
        input_sig = delay_view + delayed_sig * self.delay_feedback
        
        # Handle wrap-around for writing
        if self.delay_write_pos + frames <= self.delay_len:
            self.delay_buffer[self.delay_write_pos:self.delay_write_pos+frames] = input_sig
        else:
            part1_len = self.delay_len - self.delay_write_pos
            self.delay_buffer[self.delay_write_pos:] = input_sig[:part1_len]
            self.delay_buffer[:frames - part1_len] = input_sig[part1_len:]
            
        self.delay_write_pos = (self.delay_write_pos + frames) % self.delay_len
        
        mix_view += delayed_sig

        # Vectorized Reverb Processing
        # Same logic as delay
        rev_read_pos = (self.reverb_write_pos - int(self.sample_rate * 0.1) + self.reverb_len) % self.reverb_len
        
        if rev_read_pos + frames <= self.reverb_len:
            reverb_sig = self.reverb_buffer[rev_read_pos:rev_read_pos+frames]
        else:
            part1 = self.reverb_buffer[rev_read_pos:]
            part2 = self.reverb_buffer[:frames - len(part1)]
            reverb_sig = np.concatenate((part1, part2))
            
        rev_input_sig = reverb_view + reverb_sig * self.reverb_feedback
        
        if self.reverb_write_pos + frames <= self.reverb_len:
            self.reverb_buffer[self.reverb_write_pos:self.reverb_write_pos+frames] = rev_input_sig
        else:
            part1_len = self.reverb_len - self.reverb_write_pos
            self.reverb_buffer[self.reverb_write_pos:] = rev_input_sig[:part1_len]
            self.reverb_buffer[:frames - part1_len] = rev_input_sig[part1_len:]
            
        self.reverb_write_pos = (self.reverb_write_pos + frames) % self.reverb_len
        
        mix_view += reverb_sig * 0.5

        outdata[:] = mix_view

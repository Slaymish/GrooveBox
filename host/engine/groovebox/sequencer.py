from dataclasses import dataclass, asdict
import time
import random
from audio import AudioEngine

@dataclass
class Step:
    state: int = 0
    # 0 = off, 1 = normal, 2 = accented


@dataclass
class Track:
    pad_id: int
    steps: list[Step]
    mute: bool = False
    solo: bool = False
    probability: float = 1.0

@dataclass
class Pattern:
    tracks: list[Track]
    bpm: float
    beats_per_bar: int

def make_empty_pattern(config) -> Pattern:
    tracks = []
    for pad in config.pads:
        steps = [Step() for _ in range(config.beats_per_bar)]
        tracks.append(Track(pad_id=pad.id, steps=steps))
    return Pattern(tracks=tracks, bpm=config.bpm, beats_per_bar=config.beats_per_bar)

class Sequencer:
    def __init__(self, pattern_a: Pattern, pattern_b: Pattern, pattern_fill: Pattern, audio: AudioEngine):
        self.patterns = {'A': pattern_a, 'B': pattern_b, 'FILL': pattern_fill}
        self.current_pattern_key = 'A'
        self.next_pattern_key = 'A'
        self.pattern = pattern_a
        
        self.audio = audio
        self.playing = False
        self.recording = False
        self.fill_active = False
        self.current_step = 0
        self.total_steps = 0
        self.swing = 0.0  # 0.0 to 0.5
        self.last_tick_time = time.monotonic()
        self.undo_stack = []

    def set_bpm(self, bpm: float):
        # Update all patterns to keep BPM synced for now
        for p in self.patterns.values():
            p.bpm = bpm

    def toggle_play(self):
        self.playing = not self.playing

    def toggle_record(self):
        self.recording = not self.recording
    
    def set_fill(self, active: bool):
        self.fill_active = active
    
    def queue_pattern_switch(self, pattern_key: str):
        if pattern_key in self.patterns and pattern_key != 'FILL':
            self.next_pattern_key = pattern_key

    def _step_duration_seconds(self) -> float:
        base = 60.0 / self.pattern.bpm / self.pattern.beats_per_bar * 4
        if self.swing == 0:
            return base
        
        if self.total_steps % 2 == 0:
            return base * (1.0 + self.swing)
        else:
            return base * (1.0 - self.swing)

    def tick(self):
        """Call this from the main loop, it advances steps at the right time."""
        if not self.playing:
            return

        now = time.monotonic()
        seconds_per_step = self._step_duration_seconds()
        if now - self.last_tick_time >= seconds_per_step:
            self.last_tick_time = now
            self._play_step()
            self.current_step = (self.current_step + 1) % self.pattern.beats_per_bar
            self.total_steps += 1
            
            if self.current_step == 0:
                # Bar wrapped, check for pattern switch
                if self.next_pattern_key != self.current_pattern_key:
                    self.current_pattern_key = self.next_pattern_key
                    self.pattern = self.patterns[self.current_pattern_key]
                    self.total_steps = 0

    def _play_step(self):
        active_pattern = self.patterns['FILL'] if self.fill_active else self.pattern
        any_solo = any(t.solo for t in active_pattern.tracks)

        for track in active_pattern.tracks:
            if not track.steps:
                continue
            
            if any_solo:
                if not track.solo:
                    continue
            elif track.mute:
                continue

            if track.probability < 1.0 and random.random() > track.probability:
                continue

            step_idx = self.total_steps % len(track.steps)
            step = track.steps[step_idx]
            if step.state > 0:
                velocity = 0.7 if step.state == 1 else 1.0
                self.audio.play_sound(track.pad_id, velocity=velocity)

    def handle_pad_press(self, pad_id: int):
        # live play
        self.audio.play_sound(pad_id)

        # record into pattern if in record mode
        if self.recording and self.playing:
            self.push_undo()
            track = self._track_for_pad(pad_id)
            if not track.steps:
                return
            step_idx = self.total_steps % len(track.steps)
            step = track.steps[step_idx]
            step.state = (step.state + 1) % 3  # cycle through 0,1,2

    def resize_track(self, pad_id: int, new_length: int):
        self.push_undo()
        track = self._track_for_pad(pad_id)
        current_len = len(track.steps)
        if new_length == current_len:
            return
        
        if new_length > current_len:
            # Extend with empty steps
            track.steps.extend([Step() for _ in range(new_length - current_len)])
        else:
            # Truncate
            track.steps = track.steps[:new_length]

    def randomize_track(self, pad_id: int):
        self.push_undo()
        track = self._track_for_pad(pad_id)
        for step in track.steps:
            if random.random() < 0.3:
                step.state = random.choice([1, 1, 2])
            else:
                step.state = 0

    def rotate_track(self, pad_id: int, shift: int):
        self.push_undo()
        track = self._track_for_pad(pad_id)
        if not track.steps:
            return
        shift = shift % len(track.steps)
        track.steps = track.steps[-shift:] + track.steps[:-shift]

    def euclidean_fill(self, pad_id: int, pulses: int):
        self.push_undo()
        track = self._track_for_pad(pad_id)
        steps_len = len(track.steps)
        pulses = max(0, min(steps_len, pulses))
        
        for i in range(steps_len):
            is_hit = ((i * pulses) % steps_len) < pulses
            track.steps[i].state = 1 if is_hit else 0

    def _track_for_pad(self, pad_id: int) -> Track:
        for t in self.pattern.tracks:
            if t.pad_id == pad_id:
                return t
        raise KeyError(pad_id)

    def get_state(self):
        return {
            'patterns': {k: asdict(v) for k, v in self.patterns.items()},
            'swing': self.swing
        }

    def load_state(self, state):
        self.swing = state.get('swing', 0.0)
        patterns_data = state.get('patterns', {})
        for key, p_data in patterns_data.items():
            if key in self.patterns:
                tracks = []
                for t_data in p_data['tracks']:
                    steps = [Step(**s) for s in t_data['steps']]
                    tracks.append(Track(
                        pad_id=t_data['pad_id'],
                        steps=steps,
                        mute=t_data.get('mute', False),
                        solo=t_data.get('solo', False),
                        probability=t_data.get('probability', 1.0)
                    ))
                self.patterns[key] = Pattern(
                    tracks=tracks,
                    bpm=p_data['bpm'],
                    beats_per_bar=p_data['beats_per_bar']
                )
        self.pattern = self.patterns[self.current_pattern_key]

    def _restore_pattern(self, p_data):
        tracks = []
        for t_data in p_data['tracks']:
            steps = [Step(**s) for s in t_data['steps']]
            tracks.append(Track(
                pad_id=t_data['pad_id'],
                steps=steps,
                mute=t_data.get('mute', False),
                solo=t_data.get('solo', False),
                probability=t_data.get('probability', 1.0)
            ))
        return Pattern(
            tracks=tracks,
            bpm=p_data['bpm'],
            beats_per_bar=p_data['beats_per_bar']
        )

    def push_undo(self):
        self.undo_stack.append(asdict(self.pattern))
        if len(self.undo_stack) > 10:
            self.undo_stack.pop(0)

    def undo(self):
        if not self.undo_stack:
            return
        p_data = self.undo_stack.pop()
        self.pattern = self._restore_pattern(p_data)
        self.patterns[self.current_pattern_key] = self.pattern

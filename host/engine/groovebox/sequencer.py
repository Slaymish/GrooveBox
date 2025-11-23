from dataclasses import dataclass
import time
from audio import AudioEngine

@dataclass
class Step:
    state: int = 0
    # 0 = off, 1 = normal, 2 = accented


@dataclass
class Track:
    pad_id: int
    steps: list[Step]

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
    def __init__(self, pattern: Pattern, audio: AudioEngine):
        self.pattern = pattern
        self.audio = audio
        self.playing = False
        self.recording = False
        self.current_step = 0
        self.swing = 0.0  # 0.0 to 0.5
        self.last_tick_time = time.monotonic()

    def set_bpm(self, bpm: float):
        self.pattern.bpm = bpm

    def toggle_play(self):
        self.playing = not self.playing

    def toggle_record(self):
        self.recording = not self.recording
    
    def _step_duration_seconds(self) -> float:
        base = 60.0 / self.pattern.bpm / self.pattern.beats_per_bar * 4
        if self.swing == 0:
            return base
        
        if self.current_step % 2 == 0:
            return base * (1.0 - self.swing)
        else:
            return base * (1.0 + self.swing)

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
    def _play_step(self):
        for track in self.pattern.tracks:
            step = track.steps[self.current_step]
            if step.state > 0:
                velocity = 0.7 if step.state == 1 else 1.0
                self.audio.play_sound(track.pad_id, velocity=velocity)

    def handle_pad_press(self, pad_id: int):
        # live play
        self.audio.play_sound(pad_id)

        # record into pattern if in record mode
        if self.recording and self.playing:
            track = self._track_for_pad(pad_id)
            step = track.steps[self.current_step]
            step.state = (step.state + 1) % 3  # cycle through 0,1,2

    def _track_for_pad(self, pad_id: int) -> Track:
        for t in self.pattern.tracks:
            if t.pad_id == pad_id:
                return t
        raise KeyError(pad_id)

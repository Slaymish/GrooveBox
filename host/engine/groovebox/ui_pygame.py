from sequencer import Sequencer, Track, make_empty_pattern
from input_devices import InputDevice, PadEvent
from audio import AudioEngine
from config import GrooveboxConfig
import pygame
import numpy as np
import json
import os

class GrooveboxUI:
    def __init__(self, config: GrooveboxConfig):
        pygame.init()
        pygame.display.set_caption("GrooveBox Engine")
        self.screen = pygame.display.set_mode((800, 600))
        self.config = config
        self.audio = AudioEngine(config)
        self.pattern_a = make_empty_pattern(config)
        self.pattern_b = make_empty_pattern(config)
        self.pattern_fill = make_empty_pattern(config)
        self.seq = Sequencer(self.pattern_a, self.pattern_b, self.pattern_fill, self.audio)
        self.font = pygame.font.SysFont("Arial", 18)
        self.help_font = pygame.font.SysFont("Arial", 14)
        self.key_to_pad = {pad.key: pad.id for pad in config.pads}
        self.selected_pad_id = None
        self.show_help = False

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)
                elif event.type == pygame.KEYUP:
                    self.handle_keyup(event.key)
            self.seq.tick()
            self.draw()
            clock.tick(60)
        pygame.quit()

    def handle_keydown(self, key):
        mods = pygame.key.get_mods()
        shift = mods & pygame.KMOD_SHIFT
        ctrl = mods & pygame.KMOD_CTRL

        if key == pygame.K_SPACE:
            self.seq.toggle_play()
        elif key == pygame.K_r:
            self.seq.toggle_record()
        elif key == pygame.K_UP:
            self.seq.set_bpm(self.seq.pattern.bpm + 5)
        elif key == pygame.K_DOWN:
            self.seq.set_bpm(max(20, self.seq.pattern.bpm - 5))
        elif key == pygame.K_LEFT:
            if self.selected_pad_id is not None and (shift or ctrl):
                state = self.audio.get_pad_state(self.selected_pad_id)
                if state:
                    if shift:
                        new_start = max(0.0, state['trim_start'] - 0.01)
                        self.audio.set_trim(self.selected_pad_id, new_start, state['trim_end'])
                    elif ctrl:
                        new_end = max(state['trim_start'], state['trim_end'] - 0.01)
                        self.audio.set_trim(self.selected_pad_id, state['trim_start'], new_end)
            else:
                self.seq.swing = max(0.0, self.seq.swing - 0.05)
        elif key == pygame.K_RIGHT:
            if self.selected_pad_id is not None and (shift or ctrl):
                state = self.audio.get_pad_state(self.selected_pad_id)
                if state:
                    if shift:
                        new_start = min(state['trim_end'], state['trim_start'] + 0.01)
                        self.audio.set_trim(self.selected_pad_id, new_start, state['trim_end'])
                    elif ctrl:
                        new_end = min(1.0, state['trim_end'] + 0.01)
                        self.audio.set_trim(self.selected_pad_id, state['trim_start'], new_end)
            else:
                self.seq.swing = min(0.5, self.seq.swing + 0.05)
        elif key == pygame.K_TAB:
            next_pat = 'B' if self.seq.next_pattern_key == 'A' else 'A'
            self.seq.queue_pattern_switch(next_pat)
        elif key == pygame.K_f:
            self.seq.set_fill(True)
        elif key == pygame.K_LEFTBRACKET:
            if self.selected_pad_id is not None:
                if shift:
                    self.seq.rotate_track(self.selected_pad_id, -1)
                else:
                    track = self._track_for_pad(self.selected_pad_id)
                    new_len = max(1, len(track.steps) - 1)
                    self.seq.resize_track(self.selected_pad_id, new_len)
        elif key == pygame.K_RIGHTBRACKET:
            if self.selected_pad_id is not None:
                if shift:
                    self.seq.rotate_track(self.selected_pad_id, 1)
                else:
                    track = self._track_for_pad(self.selected_pad_id)
                    new_len = min(32, len(track.steps) + 1)
                    self.seq.resize_track(self.selected_pad_id, new_len)
        elif key == pygame.K_e:
            if self.selected_pad_id is not None:
                track = self._track_for_pad(self.selected_pad_id)
                current_pulses = sum(1 for s in track.steps if s.state > 0)
                new_pulses = current_pulses + 1 if not shift else max(0, current_pulses - 1)
                self.seq.euclidean_fill(self.selected_pad_id, new_pulses)
        elif key == pygame.K_p:
            if self.selected_pad_id is not None:
                track = self._track_for_pad(self.selected_pad_id)
                if shift:
                    track.probability = min(1.0, track.probability + 0.1)
                else:
                    track.probability = max(0.0, track.probability - 0.1)
        elif key == pygame.K_m:
            if self.selected_pad_id is not None:
                track = self._track_for_pad(self.selected_pad_id)
                track.mute = not track.mute
        elif key == pygame.K_s:
            if ctrl:
                self.save_session()
            elif self.selected_pad_id is not None:
                track = self._track_for_pad(self.selected_pad_id)
                track.solo = not track.solo
        elif key == pygame.K_o and ctrl:
            self.load_session()
        elif key == pygame.K_x:
            if self.selected_pad_id is not None:
                self.seq.randomize_track(self.selected_pad_id)
        elif key == pygame.K_n:
            if self.selected_pad_id is not None:
                self.audio.toggle_normalize(self.selected_pad_id)
        elif key == pygame.K_v:
            if self.selected_pad_id is not None:
                self.audio.toggle_reverse(self.selected_pad_id)
        elif key == pygame.K_l:  # Load session
            self.load_session()
        elif key == pygame.K_s:  # Save session
            self.save_session()
        elif key == pygame.K_PAGEUP:
            if self.selected_pad_id is not None:
                self.audio.cycle_sample(self.selected_pad_id, -1)
        elif key == pygame.K_PAGEDOWN:
            if self.selected_pad_id is not None:
                self.audio.cycle_sample(self.selected_pad_id, 1)
        elif key == pygame.K_z and ctrl:
            self.seq.undo()
        elif key == pygame.K_h or key == pygame.K_SLASH:
            self.show_help = not self.show_help
        else:
            pad_id = self._pad_from_key(key)
            if pad_id is not None:
                self.selected_pad_id = pad_id
                self.seq.handle_pad_press(pad_id)

    def handle_keyup(self, key):
        if key == pygame.K_f:
            self.seq.set_fill(False)

    def _pad_from_key(self, key):
        char = pygame.key.name(key)
        return self.key_to_pad.get(char)
    
    def draw(self):
        """Draw pads + per-instrument step grid + status."""
        self.screen.fill((20, 20, 30))  # Darker background

        padding = 20
        
        # Waveform area
        waveform_height = 80
        if self.selected_pad_id is not None:
            self._draw_waveform(padding, padding, self.screen.get_width() - 2*padding, waveform_height)
        else:
            # Draw a placeholder or title if no pad selected
            title_surf = self.font.render("GROOVEBOX ENGINE", True, (60, 60, 80))
            self.screen.blit(title_surf, (padding, padding))
        
        pad_rows = 2
        pad_cols = 4

        # Top half: the big pads you hit
        pad_area_width = self.screen.get_width() - 2 * padding
        pad_area_height = 180

        pad_width = (pad_area_width - (pad_cols + 1) * padding) // pad_cols
        pad_height = (pad_area_height - (pad_rows + 1) * padding) // pad_rows
        
        pad_start_y = padding + waveform_height + padding

        # Draw pad grid
        for i, pad_cfg in enumerate(self.config.pads):
            row = i // pad_cols
            col = i % pad_cols

            x = padding + col * (pad_width + padding)
            y = pad_start_y + row * (pad_height + padding)

            rect = pygame.Rect(x, y, pad_width, pad_height)

            track = self._track_for_pad(pad_cfg.id)

            has_any_steps = any(step.state > 0 for step in track.steps)
            
            # Use total_steps for polyrhythmic lookup
            if track.steps:
                step_idx = self.seq.total_steps % len(track.steps)
                step_active_now = track.steps[step_idx].state > 0
            else:
                step_active_now = False

            base_colour = (40, 40, 50)
            border_color = (60, 60, 80)
            
            if has_any_steps:
                base_colour = (50, 50, 80)        # has something programmed
            
            if pad_cfg.id == self.selected_pad_id:
                border_color = (255, 200, 100)
                base_colour = (70, 70, 100)

            if step_active_now and self.seq.playing:
                base_colour = (140, 100, 160)       # this step currently firing
                border_color = (200, 150, 220)

            pygame.draw.rect(self.screen, base_colour, rect, border_radius=8)
            pygame.draw.rect(self.screen, border_color, rect, 2, border_radius=8)

            name_surface = self.font.render(pad_cfg.name, True, (220, 220, 230))
            key_surface = self.font.render(f"[{pad_cfg.key.upper()}]", True, (150, 150, 170))

            name_pos = name_surface.get_rect(center=(rect.centerx, rect.centery - 10))
            key_pos = key_surface.get_rect(center=(rect.centerx, rect.centery + 15))

            self.screen.blit(name_surface, name_pos)
            self.screen.blit(key_surface, key_pos)

        # Middle: per-instrument beat grid
        grid_y_start = pad_start_y + pad_area_height + padding
        grid_height = 180
        self._draw_step_grid(
            x_start=padding,
            y_start=grid_y_start,
            width=pad_area_width,
            height=grid_height,
        )

        # Bottom: status line (BPM, mode etc)
        self._draw_status_line()

        if self.show_help:
            self._draw_help()

        pygame.display.flip()

    def _draw_help(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        help_text = [
            "CONTROLS",
            "----------------",
            "SPACE: Play/Pause | R: Record | TAB: Switch Pattern (A/B) | F: Fill (Hold)",
            "UP/DOWN: BPM | LEFT/RIGHT: Swing",
            "1-6: Trigger Pad / Select Track",
            "",
            "TRACK EDITING (Selected Track)",
            "----------------",
            "[: Decrease Length | ]: Increase Length",
            "Shift + [/]: Rotate Pattern",
            "M: Mute | S: Solo",
            "X: Randomize | E: Euclidean Fill (+Shift to reduce)",
            "P: Probability (+Shift to increase)",
            "",
            "SAMPLE EDITING",
            "----------------",
            "PgUp/PgDn: Cycle Sample",
            "V: Reverse | N: Normalize",
            "Shift + Left/Right: Trim Start",
            "Ctrl + Left/Right: Trim End",
            "",
            "SESSION",
            "----------------",
            "Ctrl+S: Save | Ctrl+O: Load | Ctrl+Z: Undo",
            "H / ?: Toggle Help"
        ]
        
        y = 50
        for line in help_text:
            color = (255, 255, 255)
            if line.startswith("---") or line == "":
                y += 10
                continue
            if line.isupper() and not line.startswith("CTRL"):
                color = (255, 200, 100)
                y += 10
            
            surf = self.font.render(line, True, color)
            rect = surf.get_rect(center=(self.screen.get_width() // 2, y))
            self.screen.blit(surf, rect)
            y += 30

    def _draw_waveform(self, x, y, width, height):
        data = self.audio.get_waveform(self.selected_pad_id)
        if data is None:
            return
            
        # Draw background
        rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 20, 30), rect)
        pygame.draw.rect(self.screen, (60, 60, 80), rect, 1)
        
        # Downsample
        if len(data.shape) > 1:
            samples = np.mean(data, axis=1)
        else:
            samples = data
            
        if len(samples) == 0:
            return
            
        step = max(1, len(samples) // width)
        view = samples[::step]
        
        max_amp = 32768.0
        center_y = y + height // 2
        scale = (height / 2) / max_amp
        
        points = []
        for i, samp in enumerate(view):
            if i >= width: break
            px = x + i
            py = center_y - samp * scale
            points.append((px, py))
            
        if len(points) > 1:
            pygame.draw.lines(self.screen, (100, 200, 100), False, points)
            
        # Draw trim markers
        state = self.audio.get_pad_state(self.selected_pad_id)
        if state:
            start_x = x + int(state['trim_start'] * width)
            end_x = x + int(state['trim_end'] * width)
            
            pygame.draw.line(self.screen, (255, 255, 0), (start_x, y), (start_x, y + height), 2)
            pygame.draw.line(self.screen, (255, 0, 0), (end_x, y), (end_x, y + height), 2)
            
            # Draw status text
            status_text = []
            if state['reverse']: status_text.append("REV")
            if state['normalized']: status_text.append("NORM")
            
            if status_text:
                text = " ".join(status_text)
                surf = self.font.render(text, True, (255, 100, 100))
                self.screen.blit(surf, (x + 5, y + 5))

    def _draw_step_grid(self, x_start: int, y_start: int, width: int, height: int):
        """Draw one row of steps per instrument (track)."""
        current_pattern = self.seq.pattern
        max_steps = current_pattern.beats_per_bar
        for track in current_pattern.tracks:
            max_steps = max(max_steps, len(track.steps))
        
        num_tracks = len(current_pattern.tracks)

        row_gap = 4
        label_width = 120  # left side for instrument names
        grid_width = width - label_width - 10

        row_height = (height - row_gap * (num_tracks + 1)) // num_tracks
        step_gap = 2
        step_width = (grid_width - step_gap * (max_steps + 1)) // max_steps
        step_height = row_height

        for track_idx, track in enumerate(current_pattern.tracks):
            row_y = y_start + row_gap + track_idx * (row_height + row_gap)

            # Draw instrument label on the left
            pad_id = track.pad_id
            pad_cfg = next(p for p in self.config.pads if p.id == pad_id)
            
            status_flags = []
            if track.solo: status_flags.append("S")
            if track.mute: status_flags.append("M")
            if track.probability < 1.0: status_flags.append(f"{int(track.probability*100)}%")
            status_str = f" [{' '.join(status_flags)}]" if status_flags else ""

            label_text = f"{pad_cfg.name} [{pad_cfg.key.upper()}]{status_str}"
            
            label_color = (180, 180, 200)
            if track.mute:
                label_color = (100, 100, 110)
            if track.solo:
                label_color = (255, 220, 150)
            
            if pad_id == self.selected_pad_id:
                label_color = (255, 255, 100)

            label_surface = self.font.render(label_text, True, label_color)
            label_rect = label_surface.get_rect()
            label_rect.midleft = (x_start, row_y + row_height // 2)
            self.screen.blit(label_surface, label_rect)

            # Draw the row of steps for this track
            steps_in_track = len(track.steps)
            for step_idx in range(steps_in_track):
                x = x_start + label_width + step_gap + step_idx * (step_width + step_gap)
                y = row_y

                rect = pygame.Rect(x, y, step_width, step_height)

                step = track.steps[step_idx]

                base_colour = (30, 30, 40)          # empty
                border_color = (50, 50, 60)
                
                if step.state == 1:
                    base_colour = (80, 80, 120)     # this instrument plays here
                    border_color = (100, 100, 150)
                elif step.state == 2:
                    base_colour = (140, 140, 190)   # accented
                    border_color = (180, 180, 220)

                # Highlight current step column
                current_track_step = self.seq.total_steps % steps_in_track
                if step_idx == current_track_step and self.seq.playing:
                    # brighten column
                    if step.state > 0:
                        base_colour = (220, 200, 100)   # active and current
                    else:
                        base_colour = (100, 100, 80)   # current but empty

                pygame.draw.rect(self.screen, base_colour, rect, border_radius=2)
                pygame.draw.rect(self.screen, border_color, rect, 1, border_radius=2)

    def _draw_status_line(self):
        text_colour = (200, 200, 210)

        bpm_text = f"BPM: {int(self.seq.pattern.bpm)}"
        mode_text = "PLAY" if self.seq.playing else "STOP"
        rec_text = "REC" if self.seq.recording else "   "
        swing_text = f"Swing: {int(self.seq.swing * 100)}%"
        
        pat_text = f"Pat: {self.seq.current_pattern_key}"
        if self.seq.next_pattern_key != self.seq.current_pattern_key:
            pat_text += f" -> {self.seq.next_pattern_key}"
        if self.seq.fill_active:
            pat_text += " [FILL]"

        status = f"{bpm_text}  |  {mode_text}  |  {rec_text}  |  {swing_text}  |  {pat_text}"
        
        # Draw status bar background
        bar_height = 30
        bar_rect = pygame.Rect(0, self.screen.get_height() - bar_height, self.screen.get_width(), bar_height)
        pygame.draw.rect(self.screen, (30, 30, 40), bar_rect)
        pygame.draw.line(self.screen, (60, 60, 80), (0, self.screen.get_height() - bar_height), (self.screen.get_width(), self.screen.get_height() - bar_height))

        surface = self.font.render(status, True, text_colour)
        rect = surface.get_rect()
        rect.midbottom = (self.screen.get_width() // 2, self.screen.get_height() - 5)

        self.screen.blit(surface, rect)
        
        # Draw help hint
        hint_surf = self.help_font.render("Press 'H' for Help", True, (100, 100, 120))
        self.screen.blit(hint_surf, (self.screen.get_width() - 120, self.screen.get_height() - 25))

    def _track_for_pad(self, pad_id: int) -> Track:
        for t in self.seq.pattern.tracks:
            if t.pad_id == pad_id:
                return t
        raise KeyError(pad_id)

    def save_session(self, filename="session.json"):
        data = {
            'sequencer': self.seq.get_state(),
            'audio': self.audio.get_state()
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Session saved to {filename}")

    def load_session(self, filename="session.json"):
        if not os.path.exists(filename):
            print(f"Session file {filename} not found.")
            return
        
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.seq.load_state(data.get('sequencer', {}))
        self.audio.load_state(data.get('audio', {}))
        print(f"Session loaded from {filename}")
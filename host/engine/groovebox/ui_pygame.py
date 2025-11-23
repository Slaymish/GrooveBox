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
        self.screen = pygame.display.set_mode((1280, 800))
        self.config = config
        self.audio = AudioEngine(config)
        self.pattern_a = make_empty_pattern(config)
        self.pattern_b = make_empty_pattern(config)
        self.pattern_fill = make_empty_pattern(config)
        self.seq = Sequencer(self.pattern_a, self.pattern_b, self.pattern_fill, self.audio)
        
        # Fonts
        self.font_large = pygame.font.SysFont("Arial", 24, bold=True)
        self.font = pygame.font.SysFont("Arial", 16)
        self.font_small = pygame.font.SysFont("Arial", 12)
        
        self.key_to_pad = {pad.key: pad.id for pad in config.pads}
        self.selected_pad_id = None
        self.selected_step_idx = None
        self.show_help = False
        
        # Colors
        self.colors = {
            'bg': (18, 18, 24),
            'panel': (30, 30, 40),
            'panel_border': (50, 50, 60),
            'text': (220, 220, 230),
            'text_dim': (120, 120, 140),
            'accent': (255, 160, 60),
            'pad_off': (40, 40, 50),
            'pad_on': (60, 60, 80),
            'pad_active': (255, 200, 100),
            'step_off': (25, 25, 35),
            'step_on': (80, 120, 200),
            'step_accent': (120, 180, 255),
            'step_cursor': (255, 255, 255),
            'mute': (200, 60, 60),
            'solo': (220, 200, 60)
        }

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
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_click(event.pos, event.button)
            self.seq.tick()
            self.draw()
            clock.tick(60)
        pygame.quit()

    def draw(self):
        self.screen.fill(self.colors['bg'])
        
        w, h = self.screen.get_size()
        header_h = 60
        bottom_h = 180
        left_w = 400
        
        # Header
        self._draw_header(0, 0, w, header_h)
        
        # Pads
        self._draw_pads(20, header_h + 20, left_w - 40, h - header_h - bottom_h - 40)
        
        # Sequencer
        self._draw_sequencer(left_w, header_h + 20, w - left_w - 20, h - header_h - bottom_h - 40)
        
        # Bottom Panel (Waveform or Step Edit)
        self._draw_bottom_panel(20, h - bottom_h, w - 40, bottom_h - 20)
        
        if self.show_help:
            self._draw_help()
            
        pygame.display.flip()

    def _draw_header(self, x, y, w, h):
        pygame.draw.rect(self.screen, self.colors['panel'], (x, y, w, h))
        pygame.draw.line(self.screen, self.colors['panel_border'], (x, y+h), (x+w, y+h))
        
        # Title
        title = self.font_large.render("GROOVEBOX", True, self.colors['accent'])
        self.screen.blit(title, (x + 20, y + 15))
        
        # Transport Info
        info_x = x + 200
        
        # BPM
        bpm_surf = self.font.render(f"BPM: {int(self.seq.pattern.bpm)}", True, self.colors['text'])
        self.screen.blit(bpm_surf, (info_x, y + 20))
        
        # Swing
        swing_surf = self.font.render(f"SWING: {int(self.seq.swing * 100)}%", True, self.colors['text'])
        self.screen.blit(swing_surf, (info_x + 100, y + 20))
        
        # Quantize
        q_val = "RAW" if self.seq.quantise_strength == 0 else f"{int(self.seq.quantise_strength*100)}%"
        quant_surf = self.font.render(f"QUANT: {q_val}", True, self.colors['text'])
        self.screen.blit(quant_surf, (info_x + 220, y + 20))
        
        # Status
        status_text = "PLAYING" if self.seq.playing else "STOPPED"
        status_color = (100, 255, 100) if self.seq.playing else (255, 100, 100)
        if self.seq.recording:
            status_text += " [REC]"
            status_color = (255, 50, 50)
            
        status_surf = self.font_large.render(status_text, True, status_color)
        status_rect = status_surf.get_rect(right=w - 20, centery=y + h//2)
        self.screen.blit(status_surf, status_rect)
        
        # Help Hint
        hint = self.font_small.render("Press 'H' for Help", True, self.colors['text_dim'])
        self.screen.blit(hint, (w - 120, y + 40))

    def _draw_pads(self, x, y, w, h):
        # 2x4 Grid
        rows = 2
        cols = 4
        gap = 10
        
        pad_w = (w - (cols-1)*gap) // cols
        pad_h = (h - (rows-1)*gap) // rows
        
        for i, pad_cfg in enumerate(self.config.pads):
            r = i // cols
            c = i % cols
            
            px = x + c * (pad_w + gap)
            py = y + r * (pad_h + gap)
            
            rect = pygame.Rect(px, py, pad_w, pad_h)
            
            # Color logic
            color = self.colors['pad_off']
            border = self.colors['panel_border']
            
            track = self._track_for_pad(pad_cfg.id)
            
            # Check if playing
            step_idx = self.seq.total_steps % len(track.steps) if track.steps else 0
            is_playing = self.seq.playing and track.steps and track.steps[step_idx].state > 0
            
            if pad_cfg.id == self.selected_pad_id:
                color = self.colors['pad_on']
                border = self.colors['accent']
            
            if is_playing:
                color = self.colors['pad_active']
                
            # Draw Pad
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, border, rect, 2, border_radius=6)
            
            # Text
            name = self.font.render(pad_cfg.name, True, self.colors['text'])
            key = self.font_small.render(f"[{pad_cfg.key.upper()}]", True, self.colors['text_dim'])
            
            name_rect = name.get_rect(center=(rect.centerx, rect.centery - 8))
            key_rect = key.get_rect(center=(rect.centerx, rect.centery + 12))
            
            self.screen.blit(name, name_rect)
            self.screen.blit(key, key_rect)
            
            # Mute/Solo indicators
            if track.mute:
                m_surf = self.font_small.render("M", True, self.colors['mute'])
                self.screen.blit(m_surf, (rect.right - 15, rect.top + 5))
            if track.solo:
                s_surf = self.font_small.render("S", True, self.colors['solo'])
                self.screen.blit(s_surf, (rect.right - 25, rect.top + 5))

    def _draw_sequencer(self, x, y, w, h):
        tracks = self.seq.pattern.tracks
        num_tracks = len(tracks)
        if num_tracks == 0: return
        
        row_h = h // num_tracks
        gap = 2
        grid_w = w
        
        for i, track in enumerate(tracks):
            row_y = y + i * row_h
            
            # Draw row background
            bg_rect = pygame.Rect(x, row_y, grid_w, row_h - gap)
            pygame.draw.rect(self.screen, self.colors['panel'], bg_rect, border_radius=4)
            
            # Highlight if selected
            if track.pad_id == self.selected_pad_id:
                pygame.draw.rect(self.screen, self.colors['panel_border'], bg_rect, 1, border_radius=4)
            
            # Steps
            steps = track.steps
            num_steps = len(steps)
            step_w = (grid_w - 10) / num_steps
            
            for s_i, step in enumerate(steps):
                sx = x + 5 + s_i * step_w
                sy = row_y + 4
                sw = step_w - 2
                sh = row_h - gap - 8
                
                s_rect = pygame.Rect(sx, sy, sw, sh)
                
                color = self.colors['step_off']
                if step.state == 1: color = self.colors['step_on']
                elif step.state == 2: color = self.colors['step_accent']
                
                # Cursor
                if self.seq.playing and (self.seq.total_steps % num_steps) == s_i:
                    pygame.draw.rect(self.screen, self.colors['step_cursor'], s_rect.inflate(2,2), 2, border_radius=2)
                    if step.state > 0:
                        color = tuple(min(255, c + 50) for c in color)
                
                # Selection
                if track.pad_id == self.selected_pad_id and s_i == self.selected_step_idx:
                    pygame.draw.rect(self.screen, self.colors['accent'], s_rect.inflate(4,4), 2, border_radius=2)

                pygame.draw.rect(self.screen, color, s_rect, border_radius=2)
                
                # Micro-timing indicator
                if step.state > 0 and abs(step.offset) > 0.01:
                    off_x = sx + sw/2 + (step.offset * sw)
                    pygame.draw.line(self.screen, (255,0,0), (off_x, sy+sh-2), (off_x, sy+sh), 2)

    def _draw_bottom_panel(self, x, y, w, h):
        pygame.draw.rect(self.screen, self.colors['panel'], (x, y, w, h), border_radius=8)
        pygame.draw.rect(self.screen, self.colors['panel_border'], (x, y, w, h), 2, border_radius=8)
        
        if self.selected_pad_id is None:
            title = self.font.render("SELECT A PAD TO EDIT", True, self.colors['text_dim'])
            self.screen.blit(title, (x + 20, y + h//2 - 10))
            return

        if self.selected_step_idx is not None:
            self._draw_step_edit(x, y, w, h)
        else:
            self._draw_waveform(x, y, w, h)

    def _draw_step_edit(self, x, y, w, h):
        track = self._track_for_pad(self.selected_pad_id)
        if self.selected_step_idx >= len(track.steps): return
        step = track.steps[self.selected_step_idx]
        
        title = self.font.render(f"STEP EDIT: {self.selected_step_idx + 1}", True, self.colors['accent'])
        self.screen.blit(title, (x + 20, y + 15))
        
        def draw_slider(label, value, sx, sy, sw):
            lbl = self.font_small.render(label, True, self.colors['text'])
            self.screen.blit(lbl, (sx, sy))
            
            bar_rect = pygame.Rect(sx, sy + 20, sw, 6)
            pygame.draw.rect(self.screen, (50,50,50), bar_rect, border_radius=3)
            
            fill_w = sw * value
            fill_rect = pygame.Rect(sx, sy + 20, fill_w, 6)
            pygame.draw.rect(self.screen, self.colors['accent'], fill_rect, border_radius=3)
            
            val_txt = self.font_small.render(f"{int(value*100)}%", True, self.colors['text_dim'])
            self.screen.blit(val_txt, (sx + sw + 10, sy + 15))

        draw_slider("REVERB SEND", step.reverb_send, x + 20, y + 50, 200)
        draw_slider("DELAY SEND", step.delay_send, x + 20, y + 100, 200)
        
        off_norm = step.offset + 0.5
        draw_slider("OFFSET", off_norm, x + 300, y + 50, 200)

    def _draw_waveform(self, x, y, w, h):
        data = self.audio.get_waveform(self.selected_pad_id)
        if data is None: return
            
        # Downsample
        if len(data.shape) > 1:
            samples = np.mean(data, axis=1)
        else:
            samples = data
            
        if len(samples) == 0: return
            
        step = max(1, len(samples) // (w - 40))
        view = samples[::step]
        
        max_amp = 32768.0 # Expecting int16 audio data
        center_y = y + h // 2
        scale = (h / 2.5) / max_amp
        
        points = []
        for i, samp in enumerate(view):
            if i >= w - 40: break
            px = x + 20 + i
            py = center_y - samp * scale
            points.append((px, py))
            
        if len(points) > 1:
            pygame.draw.lines(self.screen, (100, 200, 100), False, points)
            
        # Draw trim markers
        state = self.audio.get_pad_state(self.selected_pad_id)
        if state:
            start_x = x + 20 + int(state['trim_start'] * (w - 40))
            end_x = x + 20 + int(state['trim_end'] * (w - 40))
            
            pygame.draw.line(self.screen, (255, 255, 0), (start_x, y+10), (start_x, y + h-10), 2)
            pygame.draw.line(self.screen, (255, 0, 0), (end_x, y+10), (end_x, y + h-10), 2)
            
            status_text = []
            if state['reverse']: status_text.append("REV")
            if state['normalized']: status_text.append("NORM")
            
            if status_text:
                text = " ".join(status_text)
                surf = self.font.render(text, True, (255, 100, 100))
                self.screen.blit(surf, (x + 20, y + 10))

    def _draw_help(self):
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        
        help_text = [
            "CONTROLS",
            "----------------",
            "SPACE: Play/Pause | R: Record | TAB: Switch Pattern (A/B) | F: Fill (Hold)",
            "UP/DOWN: BPM | LEFT/RIGHT: Swing | Q/W: Quantise",
            "1-6: Trigger Pad / Select Track",
            "",
            "TRACK EDITING (Selected Track)",
            "----------------",
            "[: Decrease Length | ]: Increase Length",
            "Shift + [/]: Rotate Pattern",
            "M: Mute | S: Solo | DEL: Clear Last Bar",
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
        
        y = 100
        for line in help_text:
            color = self.colors['text']
            if line.startswith("---") or line == "":
                y += 10
                continue
            if line.isupper() and not line.startswith("CTRL"):
                color = self.colors['accent']
                y += 10
            
            surf = self.font.render(line, True, color)
            rect = surf.get_rect(center=(self.screen.get_width() // 2, y))
            self.screen.blit(surf, rect)
            y += 30

    def handle_mouse_click(self, pos, button):
        mx, my = pos
        w, h = self.screen.get_size()
        header_h = 60
        bottom_h = 180
        left_w = 400
        
        # Pads
        pad_rect = pygame.Rect(20, header_h + 20, left_w - 40, h - header_h - bottom_h - 40)
        if pad_rect.collidepoint(mx, my):
            rel_x = mx - pad_rect.x
            rel_y = my - pad_rect.y
            
            cols = 4
            rows = 2
            gap = 10
            pad_w = (pad_rect.w - (cols-1)*gap) // cols
            pad_h = (pad_rect.h - (rows-1)*gap) // rows
            
            c = rel_x // (pad_w + gap)
            r = rel_y // (pad_h + gap)
            
            if 0 <= c < cols and 0 <= r < rows:
                idx = r * cols + c
                if idx < len(self.config.pads):
                    pad_id = self.config.pads[idx].id
                    if button == 1:
                        self.selected_pad_id = pad_id
                        self.seq.handle_pad_press(pad_id)
                    elif button == 3:
                        track = self._track_for_pad(pad_id)
                        track.mute = not track.mute
            return

        # Sequencer
        seq_rect = pygame.Rect(left_w, header_h + 20, w - left_w - 20, h - header_h - bottom_h - 40)
        if seq_rect.collidepoint(mx, my):
            tracks = self.seq.pattern.tracks
            num_tracks = len(tracks)
            if num_tracks == 0: return
            
            row_h = seq_rect.h // num_tracks
            rel_y = my - seq_rect.y
            track_idx = rel_y // row_h
            
            if 0 <= track_idx < num_tracks:
                track = tracks[track_idx]
                
                # Step
                steps = track.steps
                num_steps = len(steps)
                step_w = (seq_rect.w - 10) / num_steps
                
                rel_x = mx - (seq_rect.x + 5)
                step_idx = int(rel_x // step_w)
                
                if 0 <= step_idx < num_steps:
                    step = steps[step_idx]
                    mods = pygame.key.get_mods()
                    shift = mods & pygame.KMOD_SHIFT
                    
                    if shift:
                        self.selected_pad_id = track.pad_id
                        self.selected_step_idx = step_idx
                    else:
                        if button == 1:
                            step.state = (step.state + 1) % 3
                        elif button == 3:
                            step.state = 0
                        self.selected_step_idx = None
            return

    def handle_keydown(self, key):
        mods = pygame.key.get_mods()
        shift = mods & pygame.KMOD_SHIFT
        ctrl = mods & pygame.KMOD_CTRL

        if key == pygame.K_ESCAPE:
            self.selected_step_idx = None
            self.show_help = False
            return

        if self.selected_step_idx is not None and self.selected_pad_id is not None:
            track = self._track_for_pad(self.selected_pad_id)
            if self.selected_step_idx < len(track.steps):
                step = track.steps[self.selected_step_idx]
                
                if key == pygame.K_LEFTBRACKET:
                    if shift: step.delay_send = max(0.0, step.delay_send - 0.1)
                    else: step.reverb_send = max(0.0, step.reverb_send - 0.1)
                    return
                elif key == pygame.K_RIGHTBRACKET:
                    if shift: step.delay_send = min(1.0, step.delay_send + 0.1)
                    else: step.reverb_send = min(1.0, step.reverb_send + 0.1)
                    return

        if key == pygame.K_SPACE:
            self.seq.toggle_play()
        elif key == pygame.K_r:
            self.seq.toggle_record()
        elif key == pygame.K_q:
            self.seq.quantise_strength = max(0.0, self.seq.quantise_strength - 0.1)
        elif key == pygame.K_w:
            self.seq.quantise_strength = min(1.0, self.seq.quantise_strength + 0.1)
        elif key == pygame.K_DELETE or key == pygame.K_BACKSPACE:
            if self.selected_pad_id is not None:
                self.seq.clear_last_bar(self.selected_pad_id)
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
            if self.selected_pad_id is not None:
                track = self._track_for_pad(self.selected_pad_id)
                track.solo = not track.solo
        elif key == pygame.K_x:
            if self.selected_pad_id is not None:
                self.seq.randomize_track(self.selected_pad_id)
        elif key == pygame.K_n:
            if self.selected_pad_id is not None:
                self.audio.toggle_normalize(self.selected_pad_id)
        elif key == pygame.K_v:
            if self.selected_pad_id is not None:
                self.audio.toggle_reverse(self.selected_pad_id)
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

    def _track_for_pad(self, pad_id: int) -> Track:
        for t in self.seq.pattern.tracks:
            if t.pad_id == pad_id:
                return t
        raise KeyError(pad_id)

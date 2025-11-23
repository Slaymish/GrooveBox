from sequencer import Sequencer, Track, make_empty_pattern
from input_devices import InputDevice, PadEvent
from audio import AudioEngine
from config import GrooveboxConfig
import pygame

class GrooveboxUI:
    def __init__(self, config: GrooveboxConfig):
        pygame.init()
        pygame.display.set_caption("GrooveBox Engine")
        self.screen = pygame.display.set_mode((800, 600))
        self.config = config
        self.audio = AudioEngine(config)
        self.pattern = make_empty_pattern(config)
        self.seq = Sequencer(self.pattern, self.audio)
        self.font = pygame.font.SysFont("Arial", 18)
        self.key_to_pad = {pad.key: pad.id for pad in config.pads}

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
        if key == pygame.K_SPACE:
            self.seq.toggle_play()
        elif key == pygame.K_r:
            self.seq.toggle_record()
        elif key == pygame.K_UP:
            self.seq.set_bpm(self.seq.pattern.bpm + 5)
        elif key == pygame.K_DOWN:
            self.seq.set_bpm(max(20, self.seq.pattern.bpm - 5))
        elif key == pygame.K_LEFT:
            self.seq.swing = max(0.0, self.seq.swing - 0.05)
        elif key == pygame.K_RIGHT:
            self.seq.swing = min(0.5, self.seq.swing + 0.05)
        else:
            pad_id = self._pad_from_key(key)
            if pad_id is not None:
                self.seq.handle_pad_press(pad_id)

    def handle_keyup(self, key):
        pass

    def _pad_from_key(self, key):
        char = pygame.key.name(key)
        return self.key_to_pad.get(char)
    
    def draw(self):
        """Draw pads + per-instrument step grid + status."""
        self.screen.fill((15, 15, 25))  # background

        padding = 20
        pad_rows = 2
        pad_cols = 4

        # Top half: the big pads you hit
        pad_area_width = self.screen.get_width() - 2 * padding
        pad_area_height = 200

        pad_width = (pad_area_width - (pad_cols + 1) * padding) // pad_cols
        pad_height = (pad_area_height - (pad_rows + 1) * padding) // pad_rows

        # Draw pad grid
        for i, pad_cfg in enumerate(self.config.pads):
            row = i // pad_cols
            col = i % pad_cols

            x = padding + col * (pad_width + padding)
            y = padding + row * (pad_height + padding)

            rect = pygame.Rect(x, y, pad_width, pad_height)

            track = self._track_for_pad(pad_cfg.id)

            has_any_steps = any(step.state > 0 for step in track.steps)
            step_active_now = track.steps[self.seq.current_step].state > 0

            base_colour = (40, 40, 60)
            if has_any_steps:
                base_colour = (60, 60, 100)        # has something programmed
            if step_active_now and self.seq.playing:
                base_colour = (120, 80, 140)       # this step currently firing

            pygame.draw.rect(self.screen, base_colour, rect, border_radius=10)
            pygame.draw.rect(self.screen, (200, 200, 230), rect, 2, border_radius=10)

            name_surface = self.font.render(pad_cfg.name, True, (230, 230, 240))
            key_surface = self.font.render(f"[{pad_cfg.key.upper()}]", True, (180, 180, 200))

            name_pos = name_surface.get_rect(center=(rect.centerx, rect.centery - 10))
            key_pos = key_surface.get_rect(center=(rect.centerx, rect.centery + 15))

            self.screen.blit(name_surface, name_pos)
            self.screen.blit(key_surface, key_pos)

        # Middle: per-instrument beat grid
        grid_y_start = padding + pad_area_height + padding
        grid_height = 180
        self._draw_step_grid(
            x_start=padding,
            y_start=grid_y_start,
            width=pad_area_width,
            height=grid_height,
        )

        # Bottom: status line (BPM, mode etc)
        self._draw_status_line()

        pygame.display.flip()

    def _draw_step_grid(self, x_start: int, y_start: int, width: int, height: int):
        """Draw one row of steps per instrument (track)."""
        steps = self.pattern.beats_per_bar
        num_tracks = len(self.pattern.tracks)

        row_gap = 4
        label_width = 100  # left side for instrument names
        grid_width = width - label_width - 10

        row_height = (height - row_gap * (num_tracks + 1)) // num_tracks
        step_gap = 2
        step_width = (grid_width - step_gap * (steps + 1)) // steps
        step_height = row_height

        for track_idx, track in enumerate(self.pattern.tracks):
            row_y = y_start + row_gap + track_idx * (row_height + row_gap)

            # Draw instrument label on the left
            pad_id = track.pad_id
            pad_cfg = next(p for p in self.config.pads if p.id == pad_id)
            label_text = f"{pad_cfg.name} [{pad_cfg.key.upper()}]"
            label_surface = self.font.render(label_text, True, (210, 210, 225))
            label_rect = label_surface.get_rect()
            label_rect.midleft = (x_start, row_y + row_height // 2)
            self.screen.blit(label_surface, label_rect)

            # Draw the row of steps for this track
            for step_idx in range(steps):
                x = x_start + label_width + step_gap + step_idx * (step_width + step_gap)
                y = row_y

                rect = pygame.Rect(x, y, step_width, step_height)

                step = track.steps[step_idx]

                base_colour = (30, 30, 45)          # empty
                if step.state == 1:
                    base_colour = (90, 90, 140)     # this instrument plays here
                elif step.state == 2:
                    base_colour = (150, 150, 200)   # accented

                # Highlight current step column
                if step_idx == self.seq.current_step and self.seq.playing:
                    # brighten column
                    if step.state > 0:
                        base_colour = (220, 190, 90)   # active and current
                    else:
                        base_colour = (120, 120, 90)   # current but empty

                pygame.draw.rect(self.screen, base_colour, rect, border_radius=3)
                pygame.draw.rect(self.screen, (180, 180, 210), rect, 1, border_radius=3)

    def _draw_status_line(self):
        text_colour = (220, 220, 230)

        bpm_text = f"BPM: {int(self.seq.pattern.bpm)}"
        mode_text = "PLAY" if self.seq.playing else "STOP"
        rec_text = "REC" if self.seq.recording else " "
        swing_text = f"Swing: {int(self.seq.swing * 100)}%"

        status = f"{bpm_text}  |  {mode_text}  |  {rec_text}  |  {swing_text}"
        surface = self.font.render(status, True, text_colour)
        rect = surface.get_rect()
        rect.midbottom = (self.screen.get_width() // 2, self.screen.get_height() - 8)

        self.screen.blit(surface, rect)

    def _track_for_pad(self, pad_id: int) -> Track:
        for t in self.pattern.tracks:
            if t.pad_id == pad_id:
                return t
        raise KeyError(pad_id)
# Groovebox Engine AI Instructions

## Project Overview
Python-based Groovebox (drum machine/sequencer) using `pygame` for UI and audio.
Core logic is in `host/engine/groovebox/`.

## Architecture
- **Entry Point**: `host/engine/groovebox/main.py`. **Must be run from the repository root** to resolve relative paths (e.g., `config/pad.json`).
- **UI (`ui_pygame.py`)**:
  - `GrooveboxUI` manages the application lifecycle and main loop.
  - Handles input and rendering.
  - Calls `sequencer.tick()` every frame.
- **Sequencer (`sequencer.py`)**:
  - `Sequencer` manages playback state, BPM, swing, and patterns (A/B/Fill).
  - Uses `time.monotonic()` for precise timing, independent of UI framerate.
  - Data models: `Pattern`, `Track`, `Step` (dataclasses).
- **Audio (`audio.py`)**:
  - `AudioEngine` wraps `pygame.mixer`.
  - Handles sample loading, trimming, and playback.
- **Config (`config.py`)**:
  - Loads `config/pad.json`.
  - Typed configuration using dataclasses.

## Development Workflow

### Running
Execute from the repository root:
```bash
venv/bin/python3 host/engine/groovebox/main.py
```

### Dependencies
- `pygame` (UI & Audio)
- `numpy`
- `soundfile`

## Key Patterns & Conventions

### Timing
- **Do not** use `pygame.time.Clock` for musical timing.
- `Sequencer.tick()` calculates delta time using `time.monotonic()` to ensure rhythmic precision regardless of frame rate.

### Data Structures
- Use `@dataclass` for all state and config objects.
- Example:
  ```python
  @dataclass
  class Step:
      state: int = 0  # 0=off, 1=normal, 2=accent
  ```

### Input Handling
- Input logic is centralized in `GrooveboxUI.handle_keydown`.
- **Key Mappings**:
  - `SPACE`: Toggle Play/Pause
  - `R`: Toggle Record
  - `TAB`: Switch Pattern (A/B)
  - `F`: Fill (Hold)
  - `Arrows`: BPM (Up/Down), Swing (Left/Right)
  - `Shift/Ctrl + Arrows`: Sample Trimming (when pad selected)
  - `[ ]`: Track Length (Shift to rotate)

### UI Implementation
- UI logic belongs in `ui_pygame.py`.
- Draw methods should be efficient as they run every frame.
- Input handling is centralized in `GrooveboxUI.run()` and delegated to handler methods.

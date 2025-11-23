# Groovebox Engine AI Instructions

## Project Overview
Hybrid Python/C++ Groovebox (drum machine/sequencer).
- **Core Logic**: Python (`host/engine/groovebox/`) handles sequencing, UI, and sample management.
- **Audio Engine**: C++ extension (`groovebox_audio_cpp`) for low-latency playback, with Python fallbacks.
- **UI**: `pygame` based.

## Architecture

### Entry Point
- **`host/engine/groovebox/main.py`**: Application entry point.
- **Must be run from repository root** to resolve relative paths (e.g., `config/pad.json`).

### Audio Subsystem (`audio.py`)
- **Facade Pattern**: `AudioEngine` class dynamically selects the best available backend.
- **Priority Order**:
  1. **C++ Extension** (`audio_cpp.py` wrapping `groovebox_audio_cpp`): Preferred for performance.
  2. **SoundDevice** (`audio_sd.py`): Pure Python fallback using `sounddevice`.
  3. **Pygame** (`audio_pygame.py`): Last resort fallback.
- **C++ Integration**:
  - `host/engine/cpp/audio_engine.cpp`: Core C++ audio mixing logic.
  - `host/engine/setup.py`: Builds the `groovebox_audio_cpp` extension using `pybind11`.
  - `audio_cpp.py`: Python wrapper that handles file I/O (loading/trimming samples) and passes raw buffers to the C++ engine.

### Sequencer (`sequencer.py`)
- Manages playback state, BPM, swing, and patterns.
- **Timing**: Uses `time.monotonic()` for precise rhythmic timing, decoupled from UI framerate.
- **Data Models**: `Pattern`, `Track`, `Step` (all `@dataclass`).

### UI (`ui_pygame.py`)
- `GrooveboxUI` manages the main loop, input, and rendering.
- Calls `sequencer.tick()` every frame.
- **Performance**: Draw methods run every frame; keep them efficient.

## Development Workflow

### Build & Run
The C++ extension must be compiled before running.
```bash
# Build extension (in editable mode) and run
./run.sh
```
Or manually:
```bash
# 1. Build C++ extension
venv/bin/pip install -e host/engine/

# 2. Run application
venv/bin/python3 host/engine/groovebox/main.py
```

### Dependencies
- **System**: `portaudio` (required for C++ extension).
- **Python**: `pygame`, `numpy`, `soundfile`, `sounddevice`, `pybind11`.

## Key Patterns & Conventions

### Audio Backend Selection
- `audio.py` attempts imports in order.
- Force a specific backend using environment variable: `GROOVEBOX_AUDIO_BACKEND=pygame`.

### Data Structures
- Use `@dataclass` for all state and config objects.
- **Immutability**: Prefer treating pattern data as mutable, but configuration as immutable.

### Input Handling
- Centralized in `GrooveboxUI.handle_keydown`.
- **Key Mappings**:
  - `SPACE`: Toggle Play/Pause
  - `R`: Toggle Record
  - `TAB`: Switch Pattern (A/B)
  - `F`: Fill (Hold)
  - `Arrows`: BPM & Swing control
  - `Shift/Ctrl + Arrows`: Sample Trimming (context-dependent)
  - `[ ]`: Track Length

### C++ Extension
- **Logic Split**: Complex signal processing (mixing) in C++, file handling/parsing in Python.
- **Interface**: `audio_cpp.py` prepares `numpy` arrays and passes them to the C++ engine.

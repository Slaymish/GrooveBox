# GrooveBox

A desktop groovebox for sketching beats with a computer keyboard. Python runs the sequencer and the interface, and a small C++ engine does the audio.

## What it does

- Six sample pads, kick, snare, hat, clap, stab and fx, loaded from `samples/` through `config/pad.json`.
- A step sequencer with patterns per track, so one track can hold more than one pattern and switch between them while the bar runs.
- Scenes, which store the current combination of track patterns and bring it back in one keypress.
- Fill, for varying a pattern for a single bar.

## Running it

Python 3.8 or newer. The C++ engine is built through pybind11 when the package installs.

```bash
python3 -m venv venv
venv/bin/pip install -e host/engine/
./run.sh
```

`run.sh` installs nothing. It runs `venv/bin/python3 host/engine/groovebox/main.py`, so the virtual environment has to exist first and be called `venv`.

The audio engine has two backends. `audio_sd.py` uses sounddevice and `audio_pygame.py` uses pygame's mixer. The pygame one is what the app runs today.

## State

Worked on through November 2025. The README used to end with a next steps list, which belongs in the issue tracker instead. Nothing is packaged for distribution yet, so it runs from source.

MIT licensed.

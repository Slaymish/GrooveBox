# Gremlin Groovebox

Tiny Python-based groovebox for live beat sketching on your PC using keyboard input.  
Long term: acts as the brain for a DIY hardware controller.

## Running

- Requires Python 3.11+
- Install dependencies (example):

```bash
pip install pygame numpy soundfile
```

* From `host/engine`:

```bash
python -m gremlin.main
```

## TODO

### Core groove & feel

* [x] Multi-level steps: off / normal / accent (velocity)
* [x] Global swing control
* [x] Per-track step length for polyrhythms

### Performance controls

* [x] Per-track mute and solo
* [x] Pattern A/B variations with bar-synced switching
* [x] Fill mode for one-bar stutters or alternate pattern
* [x] Smart randomisers for specific tracks (for example hats only)

### Sound & samples

* [x] Structured local sample library (kicks, snares, hats, etc.)
* [x] Pads reference sample IDs instead of file paths
* [x] In-app sample browser to audition and assign sounds
* [x] Kits: save / load pad→sample mappings while playing

### Waveform & editing

* [x] Waveform strip at the top for the selected pad
* [x] Start / end trim markers with keyboard nudging
* [x] Reverse and normalise for the selected sample

### Pattern tools

* [x] Step or track probability for variation
* [x] Shift / rotate patterns per track
* [x] Euclidean generator for quick rhythms

### UX & persistence

* [x] Undo for recent pattern edits
* [x] Session save / load (patterns, kits, BPM, swing)
* [x] Clear visual states for selected pad, mute / solo, and current step


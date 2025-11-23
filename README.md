# Groovebox

Tiny Python and C++-based groovebox for live beat sketching on your PC using keyboard input.  
Long term: acts as the brain for a DIY hardware controller.

## Next-steps

* **Scenes & pattern management**

  * [x] Pattern A/B per track, bar-synced switching
  * [ ] Simple “scene” objects (which pattern each track uses)
  * [ ] Queue scene changes on next bar / 4 bars

* **Performance gestures**

  * [ ] Per-track mute / solo with clear UI state
  * [ ] One-bar fill mode (alt pattern or stutter) that auto-reverts
  * [ ] A few “macro” gestures (eg: drop all but kick for 1 bar; temporary LPF sweep)

* **Sample library & kits**

  * [ ] Structured local library (kicks/snares/hats/etc) with rescan
  * [ ] In-app browser to audition + assign samples to pads
  * [ ] Kits: save / load pad→sample mappings while playing

* **Waveform & editing**

  * [ ] Waveform strip for selected pad (min/max envelope)
  * [ ] Start / end trim, reverse, normalise on that strip
  * [ ] Visual markers for start/end & current play region

* **Pattern tools & variation**

  * [ ] Per-step / per-track probability for hits
  * [ ] Shift / rotate patterns per track
  * [ ] Euclidean fill for a chosen track (quick percussion generator)

* **Persistence & export**

  * [ ] Session save / load (patterns, kits, BPM, swing, quantise, scenes)
  * [ ] Export loop to WAV (and later per-track stems)
  * [ ] Export pattern to MIDI

* **Future AI hook (once you’re bored)**

  * [ ] Log patterns for yourself as training data
  * [ ] Define `suggest_pattern(pattern, mode)` API
  * [ ] First “AI” = smarter heuristics (eg hat completion), model later
    * [ ] Later: integrate with local LLM for pattern suggestions
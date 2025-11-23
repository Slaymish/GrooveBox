import json
from dataclasses import dataclass

@dataclass
class PadConfig:
    id: int
    key: str 
    name: str
    sample: str

@dataclass
class GrooveboxConfig:
    bpm: float
    beats_per_bar: int
    pads: list[PadConfig]

def load_groovebox_config(config_path: str) -> GrooveboxConfig:
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    pads = [PadConfig(**pad) for pad in data['pads']]
    
    return GrooveboxConfig(
        bpm=data['bpm'],
        beats_per_bar=data['beats_per_bar'],
        pads=pads
    )
from config import load_groovebox_config
from ui_pygame import GrooveboxUI
from pathlib import Path

def main():
    cfg = load_groovebox_config("config/pad.json")
    ui = GrooveboxUI(cfg)
    ui.run()

if __name__ == "__main__":
    main()
from config import load_groovebox_config
from ui_pygame import GrooveboxUI
from pathlib import Path

def main():
    config_path = "config/pad.json"
    try:
        cfg = load_groovebox_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading configuration from '{config_path}': {e}")
        print("Please ensure the configuration file exists and is valid JSON.")
        return

    ui = GrooveboxUI(cfg)
    ui.run()

if __name__ == "__main__":
    main()
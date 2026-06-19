import argparse
from pathlib import Path

from lib import constants, game_overlay
from lib.games import sonic_adventure

PARSER = argparse.ArgumentParser()
PARSER.add_argument("filename", type=str)

OVERLAY = sonic_adventure.OVERLAY


def create_overlay(filename: str):
    framedump_filepath = Path()
    for video_ext in constants.SUPPORTED_VIDEO_EXTENSIONS:
        framedump_filepath = constants.INPUT_PATH / f"{filename}.{video_ext}"
        if framedump_filepath.exists():
            break
    if not framedump_filepath.exists():
        raise ValueError(f"Video {filename} not found with a supported video extension")
    overlay_data_filepath = constants.INPUT_PATH / f"{filename}.csv"
    if not overlay_data_filepath.exists():
        raise ValueError(f"Overlay data {filename}.csv not found")
    overlay_data = game_overlay.GameOverlayData.load_from_csv(overlay_data_filepath)
    sonic_adventure.augment_game_data(overlay_data)
    overlay_output_filepath = constants.OUTPUT_PATH / f"{filename}_overlay.avi"
    print(f"Rendering overlay to {overlay_output_filepath}...")
    OVERLAY.encode_all_frames(overlay_output_filepath, overlay_data, framedump_filepath)
    print("Done!")


if __name__ == "__main__":
    args = PARSER.parse_args()
    create_overlay(args.filename)

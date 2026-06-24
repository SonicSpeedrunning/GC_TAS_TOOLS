import argparse
import concurrent.futures
from pathlib import Path
import time

import av

from lib import constants, game_overlay
from lib.games import sonic_adventure

PARSER = argparse.ArgumentParser()
PARSER.add_argument("project", type=str)
PARSER.add_argument("--n_proc", type=int, default=6)
PARSER.add_argument("--n_files", type=int)

OVERLAY = sonic_adventure.OVERLAY


def create_overlay_single(
    output_filepath: Path,
    overlay_data_split: game_overlay.GameOverlayData,
    framedump_filepath: Path,
):
    print(f"Starting {output_filepath.name}...")
    OVERLAY.encode_all_frames(
        output_filepath, overlay_data_split, framedump_filepath, show_pbar=False
    )
    print(f"Finished {output_filepath.name}")


def _get_framedump_filepath(base_path: Path, video_number: int) -> Path | None:
    for video_ext in constants.SUPPORTED_VIDEO_EXTENSIONS:
        filepath = base_path / f"framedump{video_number}.{video_ext}"
        if filepath.exists():
            return filepath
    return None


def create_overlay_batch(project: str, n_proc: int, n_files: int | None):
    project_path = constants.INPUT_PATH / project
    video_number = 0
    framedump_filepaths: list[Path] = []
    while True:
        framedump_filepath = _get_framedump_filepath(project_path, video_number)
        if framedump_filepath is None:
            break
        framedump_filepaths.append(framedump_filepath)
        video_number += 1

    if n_files is not None:
        framedump_filepaths = framedump_filepaths[:n_files]

    if len(framedump_filepaths) == 0:
        raise ValueError(f"No video found in {project_path}")

    overlay_data_filepath = project_path / "framedump_data.csv"
    if not overlay_data_filepath.exists():
        raise ValueError(f"Overlay data not found in {project_path}")
    full_overlay_data = game_overlay.GameOverlayData.load_from_csv(
        overlay_data_filepath
    )
    # NOTE: Was getting an "off-by-two" issue in every movie if I didn't do this. Not
    # sure why, but for now just accepting it.
    full_overlay_data.data = [full_overlay_data.data[0]] * 2 + full_overlay_data.data
    sonic_adventure.augment_game_data(full_overlay_data)

    video_lengths: list[int] = []
    for framedump_filepath in framedump_filepaths:
        framedump_video = av.open(framedump_filepath, "r")
        video_lengths.append(
            framedump_video.streams.video[0].duration
            or framedump_video.streams.video[0].frames
        )

    overlay_data_splits: list[game_overlay.GameOverlayData] = []
    prev_split = 0
    for video_length in video_lengths:
        overlay_data_splits.append(
            game_overlay.GameOverlayData(
                data=full_overlay_data.data[prev_split : prev_split + video_length]
            )
        )
        prev_split += video_length

    overlays_base_path = constants.OUTPUT_PATH / project
    overlays_base_path.mkdir(exist_ok=True)

    overlays_paths: list[Path] = []
    for framedump_filepath in framedump_filepaths:
        overlays_paths.append(
            overlays_base_path
            / f"{framedump_filepath.stem}_overlay{framedump_filepath.suffix}"
        )

    with concurrent.futures.ProcessPoolExecutor(n_proc) as executor:
        futures = []
        for overlay_path, overlay_data_split, framedump_filepath in zip(
            overlays_paths, overlay_data_splits, framedump_filepaths
        ):
            futures.append(
                executor.submit(
                    create_overlay_single,
                    overlay_path,
                    overlay_data_split,
                    framedump_filepath,
                )
            )

        while any(f.running() or not f.done() for f in futures):
            time.sleep(0.5)


if __name__ == "__main__":
    args = PARSER.parse_args()
    create_overlay_batch(args.project, args.n_proc, args.n_files)

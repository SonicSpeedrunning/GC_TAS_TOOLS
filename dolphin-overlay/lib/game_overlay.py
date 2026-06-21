import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self

from PIL import Image
import av
from tqdm import tqdm

from . import types


class GameOverlayData:
    data: list[dict]

    def __init__(self, data: list[dict]):
        self.data = data

    @classmethod
    def load_from_csv(cls, csv_filepath: str | Path) -> Self:
        with open(csv_filepath, "r") as f:
            csv_data = list(csv.DictReader(f))
        return cls(data=csv_data)


@dataclass
class GameOverlayDefaults:
    component_background_color: types.Color
    font_name: str
    font_size: int
    font_color: types.Color
    font_stroke_width: int
    font_stroke_fill: types.Color
    font_monospace_gap: int
    main_line_color: types.Color
    main_line_width: int
    outline_width: int
    outline_color: types.Color
    positive_color: types.Color
    negative_color: types.Color
    axis_label_font_name: str | list[str]
    axis_label_font_size: int
    axis_label_font_color: types.Color
    supersample_ratio: int


class GameOverlayComponent(Protocol):
    position: types.Vec2
    anchor: types.Vec2
    size: types.Vec2
    supersample_ratio: int

    def apply_defaults(self, defaults: GameOverlayDefaults) -> None:
        pass

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        pass


class GameOverlay:
    def __init__(
        self,
        components: list[GameOverlayComponent],
        resolution: types.Vec2,
        game_feed_box: tuple[int, int, int, int],
        defaults: GameOverlayDefaults,
    ) -> None:
        self._components = components
        self._resolution = resolution
        self._game_feed_box = game_feed_box
        for component in self._components:
            component.apply_defaults(defaults)

    def _update(self, game_data: dict):
        for component in self._components:
            component.update(game_data)

    def _draw(self, overlay_img: Image.Image, game_data: dict):
        for component in self._components:
            if component.supersample_ratio == 1:
                component_img = Image.new("RGBA", component.size, color=(0, 0, 0, 0))
                component.draw(component_img, game_data)
                overlay_img.paste(
                    component_img,
                    (
                        component.position[0] - component.anchor[0],
                        component.position[1] - component.anchor[1],
                    ),
                    mask=component_img,
                )
            else:
                component_resolution = (
                    component.size[0] * component.supersample_ratio,
                    component.size[1] * component.supersample_ratio,
                )
                component_img = Image.new(
                    "RGBA", component_resolution, color=(0, 0, 0, 0)
                )
                component.draw(component_img, game_data)
                component_img = component_img.resize(component.size)
                overlay_img.paste(
                    component_img,
                    (
                        component.position[0] - component.anchor[0],
                        component.position[1] - component.anchor[1],
                    ),
                    mask=component_img,
                )

    def _draw_composite_image(
        self, game_feed_img: Image.Image, overlay_img: Image.Image
    ) -> Image.Image:
        composite_img = Image.new("RGBA", self._resolution)
        resized_game_img = game_feed_img
        target_game_feed_size = (
            self._game_feed_box[2] - self._game_feed_box[0],
            self._game_feed_box[3] - self._game_feed_box[1],
        )
        if game_feed_img.size != target_game_feed_size:
            # TODO: probably more efficient to do this in the whole video first
            resized_game_img = game_feed_img.resize(target_game_feed_size)
        composite_img.paste(resized_game_img, box=self._game_feed_box)
        composite_img.paste(overlay_img, mask=overlay_img)
        return composite_img

    def draw_single_frame(
        self,
        frame_number: int,
        game_overlay_data: GameOverlayData,
        game_feed_video_filepath: str | Path,
    ) -> Image.Image:
        game_feed_container = av.open(game_feed_video_filepath, "r")
        game_feed_frame = None
        for frame in game_feed_container.decode(video=0):
            if frame.pts and frame.pts > frame_number:
                game_feed_frame = frame
                break
        if game_feed_frame is None:
            raise ValueError(f"Frame {frame_number} does not exist in video")
        assert game_feed_frame.pts is not None
        game_feed_img = game_feed_frame.to_image()

        overlay_img = Image.new("RGBA", self._resolution, color=(0, 0, 0, 0))
        overlay_frame = max(0, game_feed_frame.pts - 1)
        self._update(game_overlay_data.data[overlay_frame])
        self._draw(overlay_img, game_overlay_data.data[overlay_frame])

        return self._draw_composite_image(game_feed_img, overlay_img)

    def encode_all_frames(
        self,
        video_output_path: str | Path,
        game_overlay_data: GameOverlayData,
        game_feed_video_filepath: str | Path,
    ) -> None:
        game_feed_video = av.open(game_feed_video_filepath, "r")
        output_video = av.open(video_output_path, "w")
        output_stream = output_video.add_stream(
            "libx264",
            game_feed_video.streams.video[0].base_rate,
            {"crf": "0"},
        )
        output_stream.width = self._resolution[0]
        output_stream.height = self._resolution[1]
        output_stream.pix_fmt = "yuv444p"

        total_frames = game_feed_video.streams.video[0].frames

        base_img = Image.new("RGBA", self._resolution, color=(0, 0, 0, 0))
        with tqdm(total=total_frames, desc="Generating frames") as pbar:
            for frame_num, game_feed_frame in enumerate(
                game_feed_video.decode(video=0)
            ):
                overlay_img = base_img.copy()

                assert game_feed_frame.pts is not None
                overlay_frame = max(0, game_feed_frame.pts - 1)

                # TODO: the overlay_frame as is might not work for multiple files; rework
                # this
                self._update(game_overlay_data.data[overlay_frame])
                self._draw(overlay_img, game_overlay_data.data[overlay_frame])

                composite_img = self._draw_composite_image(
                    game_feed_frame.to_image(), overlay_img
                )

                output_frame: av.VideoFrame = av.VideoFrame.from_image(composite_img)
                output_frame.pts = game_feed_frame.pts
                output_packet = output_stream.encode(output_frame)
                output_video.mux(output_packet)
                pbar.update(1)

        output_packet = output_stream.encode(None)
        output_video.mux(output_packet)
        output_video.close()
        game_feed_video.close()

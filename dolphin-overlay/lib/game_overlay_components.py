from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import platform
from typing import Callable, Literal

from PIL import Image, ImageDraw, ImageText, ImageFont

from . import constants, game_overlay, math_utils, types


class TextComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        text_fn: Callable[[dict], str],
        position: types.Vec2,
        align: Literal["left", "middle", "right"] = "left",
        monospace: bool = False,
        font_name_override: str | list[str] | None = None,
        font_size_override: int | None = None,
        font_color_override: types.Color | None = None,
        font_stroke_width_override: int | None = None,
        font_stroke_fill_override: types.Color | None = None,
        font_monospace_gap_override: int | None = None,
    ) -> None:
        super().__init__()
        self._text_fn = text_fn
        self._align = align
        self._monospace = monospace
        self._font_name_override = font_name_override
        self._font_size_override = font_size_override
        self._font_color_override = font_color_override
        self._font_stroke_width_override = font_stroke_width_override
        self._font_stroke_fill_override = font_stroke_fill_override
        self._font_monospace_gap_override = font_monospace_gap_override

        self.position = position
        self.anchor = (0, 0)
        self.size = (0, 0)
        self.supersample_ratio = 1

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        font_names = self._font_name_override or defaults.font_name
        if isinstance(font_names, str):
            font_names = [font_names]
        font_size = self._font_size_override or defaults.font_size
        self._font_color = self._font_color_override or defaults.font_color
        self._font_stroke_width = (
            self._font_stroke_width_override
            if self._font_stroke_width_override is not None
            else defaults.font_stroke_width
        )
        self._font_stroke_fill = (
            self._font_stroke_fill_override or defaults.font_stroke_fill
        )
        self._font_monospace_gap = (
            self._font_monospace_gap_override or defaults.font_monospace_gap
        )
        font_dirs_to_try = [constants.PROJECT_ROOT / "data" / "fonts"]
        if platform.system() == "Windows":
            font_dirs_to_try.append(Path(os.environ["WINDIR"]) / "Fonts")
            font_dirs_to_try.append(
                Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
            )
        elif platform.system() == "Linux":
            font_dirs_to_try.append(
                Path(os.environ["HOME"]) / ".local" / "share" / "fonts"
            )

        font_found = False
        for font_name in font_names:
            for font_dir_to_try in font_dirs_to_try:
                font_file = font_dir_to_try / font_name
                if font_file.exists():
                    font_found = True
                    self._font = ImageFont.truetype(font_file, font_size)
                    break
            if font_found:
                break
        if not font_found:
            raise ValueError("Font not found:", font_names)

    def update(self, game_data: dict) -> None:
        self._text = self._text_fn(game_data)

        self._imgtext = ImageText.Text(self._text, self._font, mode="RGBA")
        self._imgtext.stroke(self._font_stroke_width, self._font_stroke_fill)

        if self._monospace:
            # use the bbox of the non-monospace text to get Y information
            bbox = self._imgtext.get_bbox(anchor="mm")

            self.size = (
                len(self._text) * self._font_monospace_gap,
                round(bbox[3] - bbox[1]),
            )

            if self._align == "left":
                self.anchor = (0, round(-bbox[1]))
            elif self._align == "middle":
                self.anchor = (
                    len(self._text) * self._font_monospace_gap // 2,
                    round(-bbox[1]),
                )
            elif self._align == "right":
                self.anchor = (
                    len(self._text) * self._font_monospace_gap,
                    round(-bbox[1]),
                )
            else:
                raise ValueError("Unkown align:", self._align)
        else:
            if self._align == "left":
                self._align_anchor = "lm"
            elif self._align == "middle":
                self._align_anchor = "mm"
            elif self._align == "right":
                self._align_anchor = "rm"
            else:
                raise ValueError("Unkown align:", self._align)

            bbox = self._imgtext.get_bbox(anchor=self._align_anchor)
            self.anchor = (round(-bbox[0]), round(-bbox[1]))
            self.size = (round(bbox[2] - bbox[0]), round(bbox[3] - bbox[1]))

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)

        if self._monospace:
            for i, ch in enumerate(self._text):
                draw.text(
                    xy=(
                        i * self._font_monospace_gap + self._font_monospace_gap // 2,
                        self.anchor[1],
                    ),
                    text=ch,
                    font=self._font,
                    fill=self._font_color,
                    anchor="mm",
                    stroke_width=self._font_stroke_width,
                    stroke_fill=self._font_stroke_fill,
                )
        else:
            draw.text(
                self.anchor,
                self._imgtext,
                fill=self._font_color,
                anchor=self._align_anchor,
            )


class StaticImageComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        image_filename: str,
        position: types.Vec2,
        size: types.Vec2,
    ) -> None:
        super().__init__()
        self._image = Image.open(
            constants.PROJECT_ROOT / "data" / "images" / image_filename, "r"
        ).convert("RGBA")

        self.position = position
        self.anchor = (0, 0)
        self.size = size
        self.supersample_ratio = 1

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        if self._image.size != self.size:
            self._image = self._image.resize(self.size)

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        image.paste(
            im=self._image,
            box=(0, 0),
            mask=self._image,
        )


class Plane2DBackgroundComponent(game_overlay.GameOverlayComponent):
    # TODO: also draw grid
    # TODO: support some sort of log scale
    def __init__(
        self,
        center: types.Vec2,
        size: int,
        draw_axes: bool,
        background_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._center = center
        self._size = size
        self._draw_axes = draw_axes
        self._background_color_override = background_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size, size)
        self.size = (size * 2, size * 2)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._outline_width = (
            self._outline_width_override
            if self._outline_width_override is not None
            else defaults.outline_width
        )
        self._outline_color = self._outline_color_override or defaults.outline_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            xy=(
                0,
                0,
                self._size * 2 * self.supersample_ratio,
                self._size * 2 * self.supersample_ratio,
            ),
            fill=self._background_color,
            outline=self._outline_color,
            width=self._outline_width * self.supersample_ratio,
        )
        if self._draw_axes:
            draw.line(
                xy=(
                    self._size * self.supersample_ratio,
                    0,
                    self._size * self.supersample_ratio,
                    self._size * 2 * self.supersample_ratio,
                ),
                fill=self._outline_color,
                width=self._outline_width * self.supersample_ratio,
            )
            draw.line(
                xy=(
                    0,
                    self._size * self.supersample_ratio,
                    self._size * 2 * self.supersample_ratio,
                    self._size * self.supersample_ratio,
                ),
                fill=self._outline_color,
                width=self._outline_width * self.supersample_ratio,
            )


class CircularPlotBackgroundComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        center: types.Vec2,
        radius: int,
        draw_axes: bool,
        background_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._center = center
        self._radius = radius
        self._draw_axes = draw_axes
        self._background_color_override = background_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (radius, radius)
        self.size = (radius * 2, radius * 2)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._outline_width = (
            self._outline_width_override
            if self._outline_width_override is not None
            else defaults.outline_width
        )
        self._outline_color = self._outline_color_override or defaults.outline_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            xy=(
                0,
                0,
                self._radius * 2 * self.supersample_ratio,
                self._radius * 2 * self.supersample_ratio,
            ),
            fill=self._background_color,
            outline=self._outline_color,
            width=self._outline_width * self.supersample_ratio,
        )
        draw.circle(
            xy=(
                self._radius * self.supersample_ratio,
                self._radius * self.supersample_ratio,
            ),
            radius=self._radius * self.supersample_ratio,
            outline=self._outline_color,
            width=self._outline_width * self.supersample_ratio,
        )
        if self._draw_axes:
            draw.line(
                xy=(
                    self._radius * self.supersample_ratio,
                    0,
                    self._radius * self.supersample_ratio,
                    self._radius * 2 * self.supersample_ratio,
                ),
                fill=self._outline_color,
                width=self._outline_width * self.supersample_ratio,
            )
            draw.line(
                xy=(
                    0,
                    self._radius * self.supersample_ratio,
                    self._radius * 2 * self.supersample_ratio,
                    self._radius * self.supersample_ratio,
                ),
                fill=self._outline_color,
                width=self._outline_width * self.supersample_ratio,
            )


class Speed2DPlaneComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        x_variable: str,
        y_variable: str,
        max_value: float,
        center: types.Vec2,
        size: int,
        draw_axes: bool,
        background_color_override: types.Color | None = None,
        line_width_override: int | None = None,
        line_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        self._background = Plane2DBackgroundComponent(
            center=center,
            size=size,
            draw_axes=draw_axes,
            background_color_override=background_color_override,
            outline_width_override=outline_width_override,
            outline_color_override=outline_color_override,
            supersample_ratio_override=supersample_ratio_override,
        )
        self._x_variable = x_variable
        self._y_variable = y_variable
        self._center = center
        self._size = size
        self._max_value = max_value
        self._line_width_override = line_width_override
        self._line_color_override = line_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size, size)
        self.size = (size * 2, size * 2)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background.apply_defaults(defaults)
        self._line_width = self._line_width_override or defaults.main_line_width
        self._line_color = self._line_color_override or defaults.main_line_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        self._background.draw(image, game_data)

        draw = ImageDraw.Draw(image)
        x_var_value = float(game_data.get(self._x_variable, 0))
        y_var_value = float(game_data.get(self._y_variable, 0))
        draw.line(
            (
                self._size * self.supersample_ratio,
                self._size * self.supersample_ratio,
                (self._size + int((x_var_value / self._max_value) * self._size))
                * self.supersample_ratio,
                (self._size + int((y_var_value / self._max_value) * self._size))
                * self.supersample_ratio,
            ),
            fill=self._line_color,
            width=self._line_width * self.supersample_ratio,
        )


class GravityTiltComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        x_rot_var: str,
        y_rot_var: str,
        z_rot_var: str,
        center: types.Vec2,
        size: int,
        draw_axes: bool,
        method: Literal["x_rot", "z_rot", "vector", "none"] = "none",
        background_color_override: types.Color | None = None,
        line_width_override: int | None = None,
        line_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._background = CircularPlotBackgroundComponent(
            center=center,
            radius=size,
            draw_axes=draw_axes,
            background_color_override=background_color_override,
            outline_width_override=outline_width_override,
            outline_color_override=outline_color_override,
            supersample_ratio_override=supersample_ratio_override,
        )
        self._x_rot_var = x_rot_var
        self._y_rot_var = y_rot_var
        self._z_rot_var = z_rot_var
        self._center = center
        self._size = size
        self._method = method
        self._line_width_override = line_width_override
        self._line_color_override = line_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size, size)
        self.size = (size * 2, size * 2)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background.apply_defaults(defaults)
        self._line_width = self._line_width_override or defaults.main_line_width
        self._line_color = self._line_color_override or defaults.main_line_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        self._background.draw(image, game_data)

        draw = ImageDraw.Draw(image)
        x_var_value = int(game_data.get(self._x_rot_var, 0))
        y_var_value = int(game_data.get(self._y_rot_var, 0))
        z_var_value = int(game_data.get(self._z_rot_var, 0))

        # generate a rotation from the incoming bcd values
        rot = math_utils.Rotation.from_bcd(x_var_value, y_var_value, z_var_value)

        # make a global down vector and rotate it by our rotation to get our local down
        global_down = math_utils.Vector(0, -1, 0)
        local_down = global_down.rotate(rot)

        # take just the y component and we can generate the side component of the tilt vector after
        tilt_down_component = local_down.y
        tilt_side_component = math.sqrt(1 - tilt_down_component**2)

        # use the selected method to select which half of the graph to use
        if self._method == "x_rot":
            tilt_side_component *= (
                -1 if math_utils.bcd_to_signed_bcd(x_var_value) >= 0 else 1
            )
        elif self._method == "z_rot":
            tilt_side_component *= (
                -1 if math_utils.bcd_to_signed_bcd(z_var_value) < 0 else 1
            )
        elif self._method == "vector":
            vector_side = (
                math_utils.Vector(1, 0, 0)
                .rotate(rot)
                .cross(global_down)
                .dot(local_down)
            )
            tilt_side_component *= -1 if vector_side > 0 else 1
        elif self._method == "none":
            pass
        else:
            raise ValueError("Unknown method", self._method)

        draw.line(
            (
                self._size * self.supersample_ratio,
                self._size * self.supersample_ratio,
                self._size * (1 + tilt_side_component) * self.supersample_ratio,
                self._size * (1 - tilt_down_component) * self.supersample_ratio,
            ),
            fill=self._line_color,
            width=self._line_width * self.supersample_ratio,
        )


class GravityAngleAltitudeIndicator(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        x_rot: str,
        y_rot: str,
        z_rot: str,
        center: types.Vec2,
        size: int,
        perspective: str = "y",
        top_color: types.Color | None = None,
        bottom_color: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._x_rot = x_rot
        self._y_rot = y_rot
        self._z_rot = z_rot
        self._center = center
        self._size = size
        self._perspective = perspective
        self._top_color = top_color
        self._bottom_color = bottom_color
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size // 2, size // 2)
        self.size = (size, size)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._top_color = self._top_color or defaults.positive_color
        self._bottom_color = self._bottom_color or defaults.negative_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        x_rot = int(game_data.get(self._x_rot, 0))
        y_rot = int(game_data.get(self._y_rot, 0))
        z_rot = int(game_data.get(self._z_rot, 0))

        # generate a rotation from the incoming bcd values
        rot = math_utils.Rotation.from_bcd(x_rot, y_rot, z_rot)

        # make a global down vector and rotate it by our rotation to get our local down
        global_down = math_utils.Vector(0, -1, 0)
        local_down = global_down.rotate(rot)

        if self._perspective == "y":
            # isolate just the Y direction so we know how tilted the ball will be relative to our view
            ball_tilt = -local_down.y

            # get the rotation the ball will be relative to our view with X/Z
            # (rotated by tau/4 because 0 is at 3 o'clock)
            ball_rot = math.atan2(local_down.x, local_down.z) + math.tau / 4
        elif self._perspective == "x":
            # isolate just the X direction so we know how tilted the ball will be relative to our view
            ball_tilt = -local_down.x

            # get the rotation the ball will be relative to our view with Y/Z
            # (rotated by tau/4 because 0 is at 3 o'clock)
            ball_rot = math.atan2(local_down.y, local_down.z) + math.tau / 4
        elif self._perspective == "relative":
            # find the X/Z direction the character is facing, and rotate the local_down
            # so that it's relative to the character facing forwards
            global_forwards = math_utils.Vector(1, 0, 0)
            local_forwards = global_forwards.rotate(rot)
            # (rotated by tau/4 because 0 is at 3 o'clock)
            forwards_rot = math.atan2(local_forwards.x, local_forwards.z) - math.tau / 4
            adjustment_rot = math_utils.Rotation(0, forwards_rot, 0)
            local_down = local_down.rotate(adjustment_rot)

            # isolate just the X direction so we know how tilted the ball will be relative to our view
            ball_tilt = -local_down.x

            # get the rotation the ball will be relative to our view with Y/Z
            # (rotated by tau/4 because 0 is at 3 o'clock)
            ball_rot = math.atan2(local_down.y, local_down.z) + math.tau / 4
        else:
            raise ValueError(f"Unknown perspective {self._perspective}")

        # draw a half-and-half circle to start with
        # south side is blue
        draw.chord(
            (
                0,
                0,
                self._size * self.supersample_ratio,
                self._size * self.supersample_ratio,
            ),
            0,
            180,
            fill=self._bottom_color,
        )
        # north side is red
        draw.chord(
            (
                0,
                0,
                self._size * self.supersample_ratio,
                self._size * self.supersample_ratio,
            ),
            180,
            0,
            fill=self._top_color,
        )

        # choose the color for the ellipse to give the impression of a tilted ball
        if ball_tilt > 0:
            # ball is tilting towards us, use north-pole as the near-pole
            near_color = self._top_color
        else:
            # ball is tilting away us, use south-pole as the near-pole
            near_color = self._bottom_color

        # the X (ball_tilt) corresponds to the minor radius of the ellipse
        draw.ellipse(
            (
                0,
                (self._size / 2) * (1 - abs(ball_tilt)) * self.supersample_ratio,
                self._size * self.supersample_ratio,
                (self._size / 2) * (1 + abs(ball_tilt)) * self.supersample_ratio,
            ),
            fill=near_color,
        )

        # rotate the sub_image by the ball rotation (ball_rot)
        rot_image = image.rotate(ball_rot * 360 / math.tau)
        # not sure if this technically could allow the unrotated ball to peek through
        image.paste(rot_image)


# TODO: continue design of speed dial (2 versions)


class SpeedDialComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        variable: str,
        max_value: float,
        center: types.Vec2,
        size: types.Vec2,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        background_color_override: types.Color | None = None,
        fill_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._variable = variable
        self._max_value = max_value
        self._center = center
        self._size = size
        self._orientation = orientation
        self._background_color_override = background_color_override
        self._fill_color_override = fill_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size[0] // 2, size[1] // 2)
        self.size = (size[0], size[1])

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._fill_color = self._fill_color_override or defaults.positive_color
        self._outline_width = (
            self._outline_width_override
            if self._outline_width_override is not None
            else defaults.outline_width
        )
        self._outline_color = self._outline_color_override or defaults.outline_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            xy=(
                0,
                0,
                self._size[0] * self.supersample_ratio,
                self._size[1] * self.supersample_ratio,
            ),
            fill=self._background_color,
            width=self._outline_width * self.supersample_ratio,
            outline=self._outline_color,
        )
        if self._orientation == "horizontal":
            draw.line(
                xy=(
                    self._size[0] // 2 * self.supersample_ratio,
                    0,
                    self._size[0] // 2 * self.supersample_ratio,
                    self._size[1] * self.supersample_ratio,
                ),
                fill=self._outline_color,
                width=self._outline_width * self.supersample_ratio,
            )
        elif self._orientation == "vertical":
            draw.line(
                xy=(
                    0,
                    self._size[1] // 2 * self.supersample_ratio,
                    self._size[0] * self.supersample_ratio,
                    self._size[1] // 2 * self.supersample_ratio,
                ),
                fill=self._outline_color,
                width=self._outline_width * self.supersample_ratio,
            )
        else:
            raise ValueError(f"Unknown orientation {self._orientation}")

        normalized = float(game_data.get(self._variable, 0)) / self._max_value
        max_width = self._size[0] // 2 - self._outline_width

        if self._orientation == "horizontal":
            left = min(normalized, 0.0)
            right = max(normalized, 0.0)
            draw.rectangle(
                xy=(
                    ((self._size[0] // 2) + left * max_width) * self.supersample_ratio,
                    self._outline_width * self.supersample_ratio,
                    ((self._size[0] // 2) + right * max_width) * self.supersample_ratio,
                    (self._size[1] - self._outline_width) * self.supersample_ratio,
                ),
                fill=self._fill_color,
            )
        elif self._orientation == "vertical":
            bottom = min(normalized, 0.0)
            top = max(normalized, 0.0)
            draw.rectangle(
                xy=(
                    self._outline_width * self.supersample_ratio,
                    ((self._size[1] // 2) - top * max_width) * self.supersample_ratio,
                    (self._size[0] - self._outline_width) * self.supersample_ratio,
                    ((self._size[1] // 2) - bottom * max_width)
                    * self.supersample_ratio,
                ),
                fill=self._fill_color,
            )
        else:
            raise ValueError(f"Unknown orientation {self._orientation}")


class SpeedDialComponentV2(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        variable: str,
        max_value: float,
        center: types.Vec2,
        size: types.Vec2,
        orientation: Literal["horizontal", "vertical"] = "horizontal",
        background_color_override: types.Color | None = None,
        positive_color_override: types.Color | None = None,
        negative_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._variable = variable
        self._max_value = max_value
        self._center = center
        self._size = size
        self._orientation = orientation
        self._background_color_override = background_color_override
        self._positive_color_override = positive_color_override
        self._negative_color_override = negative_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size[0] // 2, size[1] // 2)
        self.size = (size[0], size[1])

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._positive_color = self._positive_color_override or defaults.positive_color
        self._negative_color = self._negative_color_override or defaults.negative_color
        self._outline_width = (
            self._outline_width_override
            if self._outline_width_override is not None
            else defaults.outline_width
        )
        self._outline_color = self._outline_color_override or defaults.outline_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            xy=(
                0,
                0,
                self._size[0] * self.supersample_ratio,
                self._size[1] * self.supersample_ratio,
            ),
            fill=self._background_color,
            width=self._outline_width * self.supersample_ratio,
            outline=self._outline_color,
        )

        var_value = float(game_data.get(self._variable, 0))
        if self._orientation == "horizontal":
            if var_value >= 0:
                draw.rectangle(
                    xy=(
                        self._outline_width * self.supersample_ratio,
                        self._outline_width * self.supersample_ratio,
                        (
                            self._outline_width
                            + (var_value / self._max_value)
                            * (self._size[0] - self._outline_width * 2)
                        )
                        * self.supersample_ratio,
                        (self._size[1] - self._outline_width) * self.supersample_ratio,
                    ),
                    fill=self._positive_color,
                )
            else:
                draw.rectangle(
                    xy=(
                        (
                            self._outline_width
                            + (1.0 + (var_value / self._max_value))
                            * (self._size[0] - self._outline_width * 2)
                        )
                        * self.supersample_ratio,
                        self._outline_width * self.supersample_ratio,
                        (self._size[0] - self._outline_width) * self.supersample_ratio,
                        (self._size[1] - self._outline_width) * self.supersample_ratio,
                    ),
                    fill=self._negative_color,
                )
        elif self._orientation == "vertical":
            if var_value >= 0:
                draw.rectangle(
                    xy=(
                        self._outline_width * self.supersample_ratio,
                        (
                            self._outline_width
                            + (1.0 - var_value / self._max_value)
                            * (self._size[1] - self._outline_width * 2)
                        )
                        * self.supersample_ratio,
                        (self._size[0] - self._outline_width) * self.supersample_ratio,
                        (self._size[1] - self._outline_width) * self.supersample_ratio,
                    ),
                    fill=self._positive_color,
                )
            else:
                draw.rectangle(
                    xy=(
                        self._outline_width * self.supersample_ratio,
                        self._outline_width * self.supersample_ratio,
                        (self._size[0] - self._outline_width) * self.supersample_ratio,
                        (
                            self._outline_width
                            - (var_value / self._max_value)
                            * (self._size[1] - self._outline_width * 2)
                        )
                        * self.supersample_ratio,
                    ),
                    fill=self._negative_color,
                )
        else:
            raise ValueError(f"Unknown orientation {self._orientation}")


class AngleDirectionComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        variable: str,
        center: types.Vec2,
        size: int,
        draw_axes: bool,
        background_color_override: types.Color | None = None,
        line_width_override: int | None = None,
        line_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
        supersample_ratio_override: int | None = None,
    ) -> None:
        super().__init__()
        self._background = CircularPlotBackgroundComponent(
            center=center,
            radius=size,
            draw_axes=draw_axes,
            background_color_override=background_color_override,
            outline_width_override=outline_width_override,
            outline_color_override=outline_color_override,
            supersample_ratio_override=supersample_ratio_override,
        )
        self._variable = variable
        self._center = center
        self._size = size
        self._line_width_override = line_width_override
        self._line_color_override = line_color_override
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (size, size)
        self.size = (size * 2, size * 2)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background.apply_defaults(defaults)
        self._line_width = self._line_width_override or defaults.main_line_width
        self._line_color = self._line_color_override or defaults.main_line_color
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        self._background.draw(image, game_data)

        draw = ImageDraw.Draw(image)
        rot_rad = math_utils.bcd_to_rad(
            math_utils.bcd_to_signed_bcd(int(game_data.get(self._variable, 0)))
        )
        draw.line(
            xy=(
                self._size * self.supersample_ratio,
                self._size * self.supersample_ratio,
                (self._size + math.sin(rot_rad) * self._size) * self.supersample_ratio,
                (self._size - math.cos(rot_rad) * self._size) * self.supersample_ratio,
            ),
            fill=self._line_color,
            width=self._line_width * self.supersample_ratio,
        )


@dataclass
class InputSkin:
    @dataclass
    class Button:
        image: Image.Image
        pos: types.Vec2

    @dataclass
    class AnalogMarker:
        image: Image.Image
        pos: types.Vec2
        range: int
        line_width: int
        line_color: types.Color

    @dataclass
    class Shoulder:
        color: types.Color
        pos: types.Vec2
        size: types.Vec2
        direction: Literal["right", "left", "up", "down"]

    width: int
    height: int
    background: Image.Image
    buttons: dict[str, Button]
    analog_markers: dict[str, AnalogMarker]
    shoulders: dict[str, Shoulder]


INPUTS_SKIN_BASE_PATH = constants.PROJECT_ROOT / "data" / "inputs_skin"


class InputViewerComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        center: types.Vec2,
        input_skin_name: str,
        supersample_ratio_override: int | None = None,
    ) -> None:
        self._center = center
        self._input_skin = self.load_input_skin(input_skin_name)
        self._supersample_ratio_override = supersample_ratio_override

        self.position = center
        self.anchor = (self._input_skin.width // 2, self._input_skin.height // 2)
        self.size = (self._input_skin.width, self._input_skin.height)

    @classmethod
    def load_input_skin(cls, input_skin_name: str) -> InputSkin:
        skin_path = INPUTS_SKIN_BASE_PATH / input_skin_name
        with open(skin_path / "skin.json", "r") as f:
            skin_config = json.load(f)
        return InputSkin(
            width=skin_config["width"],
            height=skin_config["height"],
            background=Image.open(
                skin_path / skin_config["background_file"], "r"
            ).convert("RGBA"),
            buttons={
                but_name: InputSkin.Button(
                    image=Image.open(skin_path / but_config["file"], "r").convert(
                        "RGBA"
                    ),
                    pos=but_config["pos"],
                )
                for but_name, but_config in skin_config["buttons"].items()
            },
            analog_markers={
                analog_name: InputSkin.AnalogMarker(
                    image=Image.open(skin_path / analog_config["file"], "r").convert(
                        "RGBA"
                    ),
                    pos=analog_config["pos"],
                    range=analog_config["range"],
                    line_width=analog_config["line_width"],
                    line_color=tuple(analog_config["line_color"]),
                )
                for analog_name, analog_config in skin_config["analog_markers"].items()
            },
            shoulders={
                shoulder_name: InputSkin.Shoulder(
                    color=tuple(shoulder_config["color"]),
                    pos=shoulder_config["pos"],
                    size=shoulder_config["size"],
                    direction=shoulder_config["direction"],
                )
                for shoulder_name, shoulder_config in skin_config["shoulders"].items()
            },
        )

    @staticmethod
    def _extract_controller_data(game_data: dict) -> dict:
        controller_data_1 = int(game_data.get("ControllerData1", 0))
        controller_data_2 = int(game_data.get("ControllerData2", 0))

        return {
            "buttons": {
                "A": controller_data_1 & 0x01000000,
                "B": controller_data_1 & 0x02000000,
                "X": controller_data_1 & 0x04000000,
                "Y": controller_data_1 & 0x08000000,
                "Start": controller_data_1 & 0x10000000,
                "L": controller_data_1 & 0x00400000,
                "R": controller_data_1 & 0x00200000,
                "Z": controller_data_1 & 0x00100000,
                "DUp": controller_data_1 & 0x00080000,
                "DDown": controller_data_1 & 0x00040000,
                "DRight": controller_data_1 & 0x00020000,
                "DLeft": controller_data_1 & 0x00010000,
            },
            "analog_sticks": {
                "Main": {
                    "X": ((controller_data_1 & 0x0000FF00) // 0x100 - 128) / 128,
                    "Y": ((controller_data_1 & 0x000000FF) - 128) / 128,
                },
                "C": {
                    "X": ((controller_data_2 & 0xFF000000) // 0x1000000 - 128) / 128,
                    "Y": ((controller_data_2 & 0x00FF0000) // 0x10000 - 128) / 128,
                },
            },
            "shoulders": {
                "L": (controller_data_2 & 0x0000FF00) // 0x100,
                "R": controller_data_2 & 0x000000FF,
            },
        }

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self.supersample_ratio = (
            self._supersample_ratio_override or defaults.supersample_ratio
        )

        for bname, button in self._input_skin.buttons.items():
            button.image = button.image.resize(
                (
                    button.image.width * self.supersample_ratio,
                    button.image.height * self.supersample_ratio,
                ),
                Image.Resampling.NEAREST,
            )

        for analog in self._input_skin.analog_markers.values():
            analog.image = analog.image.resize(
                (
                    analog.image.width * self.supersample_ratio,
                    analog.image.height * self.supersample_ratio,
                ),
                Image.Resampling.NEAREST,
            )

        self._input_skin.background = self._input_skin.background.resize(
            (
                self._input_skin.background.width * self.supersample_ratio,
                self._input_skin.background.height * self.supersample_ratio,
            ),
            Image.Resampling.NEAREST,
        )

    def update(self, game_data: dict) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        # Draw background
        image.paste(
            im=self._input_skin.background,
            mask=self._input_skin.background,
        )

        controller_data = self._extract_controller_data(game_data)

        # Draw buttons
        for but_name, but_value in controller_data["buttons"].items():
            if but_value:
                but_image = self._input_skin.buttons.get(but_name)
                if not but_image:
                    logging.warning("No image for %s button press", but_name)
                    continue
                image.alpha_composite(
                    but_image.image,
                    (
                        but_image.pos[0] * self.supersample_ratio,
                        but_image.pos[1] * self.supersample_ratio,
                    ),
                )

        # Draw analog
        for analog_name, analog_struct in controller_data["analog_sticks"].items():
            if analog_name not in self._input_skin.analog_markers:
                continue
            analog_marker = self._input_skin.analog_markers[analog_name]
            x_offset = analog_struct["X"]
            y_offset = analog_struct["Y"]
            radius = x_offset * x_offset + y_offset * y_offset
            if radius > 1:
                x_offset /= radius
                y_offset /= radius
            if analog_marker.line_width > 0:
                image_draw = ImageDraw.Draw(image)
                image_draw.line(
                    xy=(
                        analog_marker.pos[0] * self.supersample_ratio
                        + analog_marker.image.width // 2,
                        analog_marker.pos[1] * self.supersample_ratio
                        + analog_marker.image.height // 2,
                        (analog_marker.pos[0] + int(x_offset * analog_marker.range))
                        * self.supersample_ratio
                        + analog_marker.image.width // 2,
                        (analog_marker.pos[1] - int(y_offset * analog_marker.range))
                        * self.supersample_ratio
                        + analog_marker.image.height // 2,
                    ),
                    fill=analog_marker.line_color,
                    width=analog_marker.line_width * self.supersample_ratio,
                )
            image.paste(
                im=analog_marker.image,
                box=(
                    (analog_marker.pos[0] + int(x_offset * analog_marker.range))
                    * self.supersample_ratio,
                    (analog_marker.pos[1] - int(y_offset * analog_marker.range))
                    * self.supersample_ratio,
                ),
                mask=analog_marker.image,
            )

        # Draw shoulders
        image_draw = ImageDraw.Draw(image)
        for shoulder_name, shoulder_value in controller_data["shoulders"].items():
            if shoulder_name not in self._input_skin.shoulders:
                continue
            shoulder = self._input_skin.shoulders[shoulder_name]
            match shoulder.direction:
                # TODO: no idea if this is actually working
                case "right":
                    image_draw.rectangle(
                        xy=(
                            shoulder.pos[0] * self.supersample_ratio,
                            shoulder.pos[1] * self.supersample_ratio,
                            (
                                shoulder.pos[0]
                                + int(shoulder.size[0] * shoulder_value / 255)
                            )
                            * self.supersample_ratio,
                            (shoulder.pos[1] + shoulder.size[1])
                            * self.supersample_ratio,
                        ),
                        fill=shoulder.color,
                    )
                case "left":
                    image_draw.rectangle(
                        xy=(
                            (
                                shoulder.pos[0]
                                + int((1 - shoulder_value / 255) * shoulder.size[0])
                            )
                            * self.supersample_ratio,
                            shoulder.pos[1] * self.supersample_ratio,
                            (shoulder.pos[0] + shoulder.size[0])
                            * self.supersample_ratio,
                            (shoulder.pos[1] + shoulder.size[1])
                            * self.supersample_ratio,
                        ),
                        fill=shoulder.color,
                    )
                case _:
                    pass


class LayoutSelector(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        position: types.Vec2,
        size: types.Vec2,
        layouts: dict[str, list[game_overlay.GameOverlayComponent]],
        selector: Callable[[dict], str | None],
        default: list[game_overlay.GameOverlayComponent] = [],
    ) -> None:
        self._layouts = layouts
        self._default = default
        self._selector = selector

        self.position = position
        self.anchor = (0, 0)
        self.size = size
        self.supersample_ratio = 1

    def _select(self, game_data: dict) -> str | None:
        return self._selector(game_data)

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        for component in self._default:
            component.apply_defaults(defaults)
        for layout in self._layouts.values():
            for component in layout:
                component.apply_defaults(defaults)

    def update(self, game_data: dict) -> None:
        if (select_result := self._select(game_data)) is not None:
            current_layout = self._layouts[select_result]
        else:
            current_layout = self._default
        for component in current_layout:
            component.update(game_data)

    def draw(self, image: Image.Image, game_data: dict) -> None:
        if (select_result := self._select(game_data)) is not None:
            current_layout = self._layouts[select_result]
        else:
            current_layout = self._default
        for component in current_layout:
            if component.supersample_ratio == 1:
                component_img = Image.new("RGBA", component.size, color=(0, 0, 0, 0))
                component.draw(component_img, game_data)
                image.paste(
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
                image.paste(
                    component_img,
                    (
                        component.position[0] - component.anchor[0],
                        component.position[1] - component.anchor[1],
                    ),
                    mask=component_img,
                )

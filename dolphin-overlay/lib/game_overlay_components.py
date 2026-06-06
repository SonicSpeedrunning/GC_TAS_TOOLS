from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import platform
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

from . import constants, game_overlay, math_utils, types

SUPERSAMPLE_RATIO = 4


class TextComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        text_template: str,
        variables: list[str],
        variable_types: list[type],
        position: types.Vec2,
        align: Literal["left", "middle", "right"] = "left",
        monospace: bool = False,
        font_name_override: str | None = None,
        font_size_override: int | None = None,
        font_color_override: types.Color | None = None,
        font_stroke_width_override: int | None = None,
        font_stroke_fill_override: types.Color | None = None,
        font_monospace_gap_override: int | None = None,
    ) -> None:
        super().__init__()
        self._text_template = text_template
        self._variables = variables
        self._variable_types = variable_types
        self._position = position
        self._align = align
        self._monospace = monospace
        self._font_name_override = font_name_override
        self._font_size_override = font_size_override
        self._font_color_override = font_color_override
        self._font_stroke_width_override = font_stroke_width_override
        self._font_stroke_fill_override = font_stroke_fill_override
        self._font_monospace_gap_override = font_monospace_gap_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        font_name = self._font_name_override or defaults.font_name
        font_size = self._font_size_override or defaults.font_size
        self._font_color = self._font_color_override or defaults.font_color
        self._font_stroke_width = (
            self._font_stroke_width_override or defaults.font_stroke_width
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
            pass  # TODO: add where fonts are usually installed in linux

        font_found = False
        for font_dir_to_try in font_dirs_to_try:
            font_file = font_dir_to_try / font_name
            if font_file.exists():
                font_found = True
                self._font = ImageFont.truetype(font_file, font_size)
                break
        if not font_found:
            raise ValueError("Font not found:", font_name)

    def pre_draw(self, image: Image.Image) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        variable_values = [
            var_type(game_data.get(var_name))
            for var_name, var_type in zip(self._variables, self._variable_types)
        ]
        text = self._text_template.format(*variable_values)
        if self._monospace:
            if self._align == "left":
                starting_x = self._position[0] + self._font_monospace_gap // 2
            elif self._align == "middle":
                starting_x = (
                    self._position[0] - (len(text) * self._font_monospace_gap) // 2
                )
            elif self._align == "right":
                starting_x = (
                    self._position[0]
                    - (len(text) * self._font_monospace_gap)
                    - self._font_monospace_gap // 2
                )
            else:
                raise ValueError("Unkown align:", self._align)
            for i, char in enumerate(text):
                draw.text(
                    xy=(
                        starting_x + i * self._font_monospace_gap,
                        self._position[1],
                    ),
                    anchor="mm",
                    font=self._font,
                    text=char,
                    fill=self._font_color,
                    stroke_width=self._font_stroke_width,
                    stroke_fill=self._font_stroke_fill,
                )
        else:
            if self._align == "left":
                anchor = "lm"
            elif self._align == "middle":
                anchor = "mm"
            elif self._align == "right":
                anchor = "rm"
            else:
                raise ValueError("Unkown align:", self._align)
            draw.text(
                xy=self._position,
                anchor=anchor,
                font=self._font,
                text=text,
                fill=self._font_color,
                stroke_width=self._font_stroke_width,
                stroke_fill=self._font_stroke_fill,
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
        self._position = position
        self._size = size

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        pass

    def pre_draw(self, image: Image.Image) -> None:
        resized_image = self._image
        if self._image.size != self._size:
            resized_image = self._image.resize(self._size)
        image.paste(
            im=resized_image,
            box=self._position,
            mask=resized_image,
        )

    def draw(self, image: Image.Image, game_data: dict) -> None:
        pass


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
    ) -> None:
        super().__init__()
        self._center = center
        self._size = size
        self._draw_axes = draw_axes
        self._background_color_override = background_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._outline_width = self._outline_width_override or defaults.outline_width
        self._outline_color = self._outline_color_override or defaults.outline_color

    def pre_draw(self, image: Image.Image) -> None:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            xy=(
                self._center[0] - self._size,
                self._center[1] - self._size,
                self._center[0] + self._size,
                self._center[1] + self._size,
            ),
            fill=self._background_color,
            outline=self._outline_color,
            width=self._outline_width,
        )
        if self._draw_axes:
            draw.line(
                xy=(
                    self._center[0],
                    self._center[1] - self._size,
                    self._center[0],
                    self._center[1] + self._size,
                ),
                fill=self._outline_color,
                width=self._outline_width,
            )
            draw.line(
                xy=(
                    self._center[0] - self._size,
                    self._center[1],
                    self._center[0] + self._size,
                    self._center[1],
                ),
                fill=self._outline_color,
                width=self._outline_width,
            )

    def draw(self, image: Image.Image, game_data: dict) -> None:
        pass


class CircularPlotBackgroundComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        center: types.Vec2,
        radius: int,
        draw_axes: bool,
        background_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
    ) -> None:
        super().__init__()
        self._center = center
        self._radius = radius
        self._draw_axes = draw_axes
        self._background_color_override = background_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._outline_width = self._outline_width_override or defaults.outline_width
        self._outline_color = self._outline_color_override or defaults.outline_color

    def pre_draw(self, image: Image.Image) -> None:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            xy=(
                self._center[0] - self._radius,
                self._center[1] - self._radius,
                self._center[0] + self._radius,
                self._center[1] + self._radius,
            ),
            fill=self._background_color,
            outline=self._outline_color,
            width=self._outline_width,
        )
        draw.circle(
            xy=(self._center[0], self._center[1]),
            radius=self._radius,
            outline=self._outline_color,
            width=self._outline_width,
        )
        if self._draw_axes:
            draw.line(
                xy=(
                    self._center[0],
                    self._center[1] - self._radius,
                    self._center[0],
                    self._center[1] + self._radius,
                ),
                fill=self._outline_color,
                width=self._outline_width,
            )
            draw.line(
                xy=(
                    self._center[0] - self._radius,
                    self._center[1],
                    self._center[0] + self._radius,
                    self._center[1],
                ),
                fill=self._outline_color,
                width=self._outline_width,
            )

    def draw(self, image: Image.Image, game_data: dict) -> None:
        pass


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
    ) -> None:
        self._background = Plane2DBackgroundComponent(
            center=center,
            size=size,
            draw_axes=draw_axes,
            background_color_override=background_color_override,
            outline_width_override=outline_width_override,
            outline_color_override=outline_color_override,
        )
        self._x_variable = x_variable
        self._y_variable = y_variable
        self._center = center
        self._size = size
        self._max_value = max_value
        self._line_width_override = line_width_override
        self._line_color_override = line_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background.apply_defaults(defaults)
        self._line_width = self._line_width_override or defaults.main_line_width
        self._line_color = self._line_color_override or defaults.main_line_color

    def pre_draw(self, image: Image.Image) -> None:
        self._background.pre_draw(image)

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        x_var_value = float(game_data.get(self._x_variable, 0))
        y_var_value = float(game_data.get(self._y_variable, 0))
        draw.line(
            (
                self._center[0],
                self._center[1],
                self._center[0] + int((x_var_value / self._max_value) * self._size),
                self._center[1] + int((y_var_value / self._max_value) * self._size),
            ),
            fill=self._line_color,
            width=self._line_width,
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
    ) -> None:
        super().__init__()
        self._background = CircularPlotBackgroundComponent(
            center=center,
            radius=size,
            draw_axes=draw_axes,
            background_color_override=background_color_override,
            outline_width_override=outline_width_override,
            outline_color_override=outline_color_override,
        )
        self._x_rot_var = x_rot_var
        self._y_rot_var = y_rot_var
        self._z_rot_var = z_rot_var
        self._center = center
        self._size = size
        self._method = method
        self._line_width_override = line_width_override
        self._line_color_override = line_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background.apply_defaults(defaults)
        self._line_width = self._line_width_override or defaults.main_line_width
        self._line_color = self._line_color_override or defaults.main_line_color

    def pre_draw(self, image: Image.Image) -> None:
        self._background.pre_draw(image)

    def draw(self, image: Image.Image, game_data: dict) -> None:
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
                self._center[0],
                self._center[1],
                self._center[0] + tilt_side_component * self._size,
                self._center[1] - tilt_down_component * self._size,
            ),
            fill=self._line_color,
            width=self._line_width,
        )


class GravityAngleAltitudeIndicator(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        x_rot: str,
        y_rot: str,
        z_rot: str,
        center: tuple[int, int],
        size: int,
        perspective: str = 'y',
        top_color: types.Color = (255, 0, 0),
        bottom_color: types.Color = (0, 0, 255),
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

    def pre_draw(self, image: Image.Image) -> None:
        pass

    def draw(self, image: Image.Image, game_data: dict) -> None:
        sub_image = Image.new('RGBA', (self._size * SUPERSAMPLE_RATIO, self._size * SUPERSAMPLE_RATIO), (0, 0, 0, 0))
        sub_draw = ImageDraw.Draw(sub_image)
        x_rot = int(game_data.get(self._x_rot, 0))
        y_rot = int(game_data.get(self._y_rot, 0))
        z_rot = int(game_data.get(self._z_rot, 0))

        # generate a rotation from the incoming bcd values
        rot = math_utils.Rotation.from_bcd(x_rot, y_rot, z_rot)

        # make a global down vector and rotate it by our rotation to get our local down
        global_down = math_utils.Vector(0, -1, 0)
        local_down = global_down.rotate(rot)

        if self._perspective == 'y':
            # isolate just the Y direction so we know how tilted the ball will be relative to our view
            ball_tilt = -local_down.y

            # get the rotation the ball will be relative to our view with X/Z
            # (rotated by tau/4 because 0 is at 3 o'clock)
            ball_rot = math.atan2(local_down.x, local_down.z) + math.tau / 4
        elif self._perspective == 'x':
            # isolate just the X direction so we know how tilted the ball will be relative to our view
            ball_tilt = -local_down.x

            # get the rotation the ball will be relative to our view with Y/Z
            # (rotated by tau/4 because 0 is at 3 o'clock)
            ball_rot = math.atan2(local_down.y, local_down.z) + math.tau / 4
        elif self._perspective == 'relative':
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

        # draw a half-and-half circle to start with
        # south side is blue
        sub_draw.chord(
            (0, 0, self._size * SUPERSAMPLE_RATIO, self._size * SUPERSAMPLE_RATIO),
            0,
            180,
            fill=self._bottom_color
        )
        # north side is red
        sub_draw.chord(
            (0, 0, self._size * SUPERSAMPLE_RATIO, self._size * SUPERSAMPLE_RATIO),
            180,
            0,
            fill=self._top_color
        )

        # choose the color for the ellipse to give the impression of a tilted ball
        if ball_tilt > 0:
            # ball is tilting towards us, use north-pole as the near-pole
            near_color = self._top_color
        else:
            # ball is tilting away us, use south-pole as the near-pole
            near_color = self._bottom_color

        # the X (ball_tilt) corresponds to the minor radius of the ellipse
        sub_draw.ellipse(
            (
                0,
                (self._size / 2) * (1 - abs(ball_tilt)) * SUPERSAMPLE_RATIO,
                self._size * SUPERSAMPLE_RATIO,
                (self._size / 2) * (1 + abs(ball_tilt)) * SUPERSAMPLE_RATIO,
            ),
            fill=near_color,
        )

        # rotate the sub_image by the ball rotation (ball_rot)
        rot_image = sub_image.rotate(ball_rot * 360 / math.tau)
        rot_image = rot_image.resize((self._size, self._size))
        image.paste(rot_image, (self._center[0] - self._size // 2, self._center[1] - self._size // 2), mask=rot_image)


# TODO: continue design of speed dial (2 versions)


class SpeedDialComponent(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        variable: str,
        max_value: float,
        center: types.Vec2,
        size: types.Vec2,
        background_color_override: types.Color | None = None,
        fill_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
    ) -> None:
        super().__init__()
        self._variable = variable
        self._max_value = max_value
        self._center = center
        self._size = size
        self._background_color_override = background_color_override
        self._fill_color_override = fill_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._fill_color = self._fill_color_override or defaults.positive_color
        self._outline_width = self._outline_width_override or defaults.outline_width
        self._outline_color = self._outline_color_override or defaults.outline_color

    def pre_draw(self, image: Image.Image) -> None:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            xy=(
                self._center[0] - self._size[0] // 2,
                self._center[1] - self._size[1] // 2,
                self._center[0] + self._size[0] // 2,
                self._center[1] + self._size[1] // 2,
            ),
            fill=self._background_color,
            width=self._outline_width,
            outline=self._outline_color,
        )
        draw.line(
            xy=(
                self._center[0],
                self._center[1] - self._size[1] // 2,
                self._center[0],
                self._center[1] + self._size[1] // 2,
            ),
            fill=self._outline_color,
            width=self._outline_width,
        )

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        var_value = float(game_data.get(self._variable, 0))
        draw.rectangle(
            xy=(
                self._center[0]
                + (min(var_value, 0.0) / (self._max_value)) * self._size[0] // 2,
                self._center[1] - (self._size[1] - self._outline_width) // 2,
                self._center[0]
                + (max(var_value, 0.0) / (self._max_value)) * self._size[0] // 2,
                self._center[1] + (self._size[1] - self._outline_width) // 2,
            ),
            fill=self._fill_color,
        )


class SpeedDialComponentV2(game_overlay.GameOverlayComponent):
    def __init__(
        self,
        variable: str,
        max_value: float,
        center: types.Vec2,
        size: types.Vec2,
        background_color_override: types.Color | None = None,
        positive_color_override: types.Color | None = None,
        negative_color_override: types.Color | None = None,
        outline_width_override: int | None = None,
        outline_color_override: types.Color | None = None,
    ) -> None:
        super().__init__()
        self._variable = variable
        self._max_value = max_value
        self._center = center
        self._size = size
        self._background_color_override = background_color_override
        self._positive_color_override = positive_color_override
        self._negative_color_override = negative_color_override
        self._outline_width_override = outline_width_override
        self._outline_color_override = outline_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background_color = (
            self._background_color_override or defaults.component_background_color
        )
        self._positive_color = self._positive_color_override or defaults.positive_color
        self._negative_color = self._negative_color_override or defaults.negative_color
        self._outline_width = self._outline_width_override or defaults.outline_width
        self._outline_color = self._outline_color_override or defaults.outline_color

    def pre_draw(self, image: Image.Image) -> None:
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            xy=(
                self._center[0] - self._size[0] // 2,
                self._center[1] - self._size[1] // 2,
                self._center[0] + self._size[0] // 2,
                self._center[1] + self._size[1] // 2,
            ),
            fill=self._background_color,
            width=self._outline_width,
            outline=self._outline_color,
        )

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        var_value = float(game_data.get(self._variable, 0))
        if var_value >= 0:
            draw.rectangle(
                xy=(
                    self._center[0] - self._size[0] // 2 + self._outline_width,
                    self._center[1] - (self._size[1] - self._outline_width) // 2,
                    self._center[0]
                    - self._size[0] // 2
                    + self._outline_width
                    + (max(var_value, 0.0) / (self._max_value))
                    * (self._size[0] - self._outline_width),
                    self._center[1] + (self._size[1] - self._outline_width) // 2,
                ),
                fill=self._positive_color,
            )
        else:
            draw.rectangle(
                xy=(
                    self._center[0]
                    + self._size[0] // 2
                    - self._outline_width
                    - (max(-var_value, 0.0) / (self._max_value))
                    * (self._size[0] - self._outline_width),
                    self._center[1] - (self._size[1] - self._outline_width) // 2,
                    self._center[0] + self._size[0] // 2 - self._outline_width,
                    self._center[1] + (self._size[1] - self._outline_width) // 2,
                ),
                fill=self._negative_color,
            )


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
    ) -> None:
        super().__init__()
        self._background = CircularPlotBackgroundComponent(
            center=center,
            radius=size,
            draw_axes=draw_axes,
            background_color_override=background_color_override,
            outline_width_override=outline_width_override,
            outline_color_override=outline_color_override,
        )
        self._variable = variable
        self._center = center
        self._size = size
        self._line_width_override = line_width_override
        self._line_color_override = line_color_override

    def apply_defaults(self, defaults: game_overlay.GameOverlayDefaults) -> None:
        self._background.apply_defaults(defaults)
        self._line_width = self._line_width_override or defaults.main_line_width
        self._line_color = self._line_color_override or defaults.main_line_color

    def pre_draw(self, image: Image.Image) -> None:
        self._background.pre_draw(image)

    def draw(self, image: Image.Image, game_data: dict) -> None:
        draw = ImageDraw.Draw(image)
        rot_rad = math_utils.bcd_to_rad(
            math_utils.bcd_to_signed_bcd(int(game_data.get(self._variable, 0)))
        )
        draw.line(
            xy=(
                self._center[0],
                self._center[1],
                self._center[0] + math.sin(rot_rad) * self._size,
                self._center[1] - math.cos(rot_rad) * self._size,
            ),
            fill=self._line_color,
            width=self._line_width,
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
    ) -> None:
        self._center = center
        self._input_skin = self.load_input_skin(input_skin_name)

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

    def pre_draw(self, image: Image.Image) -> None:
        top_left = (
            self._center[0] - self._input_skin.width // 2,
            self._center[1] - self._input_skin.height // 2,
        )
        # Draw background
        image.paste(
            im=self._input_skin.background,
            box=(
                top_left[0],
                top_left[1],
                # top_left[0] + self._input_skin.width,
                # top_left[1] + self._input_skin.height,
            ),
            mask=self._input_skin.background,
        )

    def draw(self, image: Image.Image, game_data: dict) -> None:
        controller_data = self._extract_controller_data(game_data)
        top_left = (
            self._center[0] - self._input_skin.width // 2,
            self._center[1] - self._input_skin.height // 2,
        )
        # Draw buttons
        for but_name, but_value in controller_data["buttons"].items():
            if but_value:
                but_image = self._input_skin.buttons.get(but_name)
                if not but_image:
                    logging.warning("No image for %s button press", but_name)
                    continue
                image.paste(
                    im=but_image.image,
                    box=(
                        top_left[0] + but_image.pos[0],
                        top_left[1] + but_image.pos[1],
                    ),
                    mask=but_image.image,
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
                        top_left[0]
                        + analog_marker.pos[0]
                        + analog_marker.image.width // 2,
                        top_left[1]
                        + analog_marker.pos[1]
                        + analog_marker.image.height // 2,
                        top_left[0]
                        + analog_marker.pos[0]
                        + int(x_offset * analog_marker.range)
                        + analog_marker.image.width // 2,
                        top_left[1]
                        + analog_marker.pos[1]
                        - int(y_offset * analog_marker.range)
                        + analog_marker.image.height // 2,
                    ),
                    fill=analog_marker.line_color,
                    width=analog_marker.line_width,
                )
            image.paste(
                im=analog_marker.image,
                box=(
                    top_left[0]
                    + analog_marker.pos[0]
                    + int(x_offset * analog_marker.range),
                    top_left[1]
                    + analog_marker.pos[1]
                    - int(y_offset * analog_marker.range),
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
                            top_left[0] + shoulder.pos[0],
                            top_left[1] + shoulder.pos[1],
                            top_left[0]
                            + shoulder.pos[0]
                            + int(shoulder.size[0] * shoulder_value / 255),
                            top_left[1] + shoulder.pos[1] + shoulder.size[1],
                        ),
                        fill=shoulder.color,
                    )
                case "left":
                    image_draw.rectangle(
                        xy=(
                            top_left[0]
                            + shoulder.pos[0]
                            + int((1 - shoulder_value / 255) * shoulder.size[0]),
                            top_left[1] + shoulder.pos[1],
                            top_left[0] + shoulder.pos[0] + shoulder.size[0],
                            top_left[1] + shoulder.pos[1] + shoulder.size[1],
                        ),
                        fill=shoulder.color,
                    )
                case _:
                    pass

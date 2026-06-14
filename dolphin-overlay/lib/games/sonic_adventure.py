from .. import game_overlay, game_overlay_components

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

PLOT_SIZE = 50

SMALL_NUMBERS_CONFIG = {
    "monospace": False,
    "font_name_override": "ArialBI.ttf",
    "font_size_override": 14,
    "font_color_override": WHITE,
    "font_stroke_width_override": 0,
}


def character_select(game_data: dict) -> str | None:
    game_state = int(game_data["GameState"])
    character = int(game_data["CurrentCharacter"])

    if game_state == 7 or game_state == 16:
        if character == 7:
            return "eggman"
        elif character == 1:
            return "shadow"
        elif character == 5:
            return "rouge"
    return None


OVERLAY = game_overlay.GameOverlay(
    defaults=game_overlay.GameOverlayDefaults(
        component_background_color=BLACK,
        font_name="Kimberley Bl.otf",
        font_size=30,
        font_color=WHITE,
        font_stroke_width=3,
        font_stroke_fill=BLACK,
        font_monospace_gap=20,
        main_line_color=RED,
        main_line_width=3,
        outline_width=3,
        outline_color=WHITE,
        positive_color=RED,
        negative_color=BLUE,
        supersample_ratio=4,
    ),
    components=[
        game_overlay_components.LayoutSelector(
            position=(0, 0),
            size=(480, 1080),
            layouts={
                "eggman": [
                    game_overlay_components.StaticImageComponent(
                        image_filename="eggman.png",
                        position=(0, 0),
                        size=(480, 1080),
                    ),
                ],
                "shadow": [
                    game_overlay_components.StaticImageComponent(
                        image_filename="shadow.png",
                        position=(0, 0),
                        size=(480, 1080),
                    ),
                ],
                "rouge": [
                    game_overlay_components.StaticImageComponent(
                        image_filename="rouge.png",
                        position=(0, 0),
                        size=(480, 1080),
                    ),
                ],
            },
            selector=character_select,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Time (LRT):",
            position=(30, 50),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: (
                f"{int(game_data.get('StageMinutes', '0')):02d}:{int(game_data.get('StageSeconds', '0')):02d}:{int(game_data.get('StageCentiseconds', '0')):02d}"
            ),
            position=(200, 50),
            monospace=True,
        ),
        # Speed section
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Speed",
            position=(30, 110),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Relative",
            position=(150, 160),
            align="middle",
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "F: ",
            position=(30, 220),
        ),
        game_overlay_components.SpeedDialComponent(
            variable="FSpd",
            max_value=16.0,
            center=(160, 220),
            size=(180, 30),
        ),
        # game_overlay_components.SpeedDialComponentV2(
        #     variable="FSpd",
        #     max_value=16.0,
        #     center=(160, 220),
        #     size=(180, 30),
        # ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: f"{float(game_data.get('FSpd', 0.0)):8.4f}",
            position=(160, 245),
            align="middle",
            **SMALL_NUMBERS_CONFIG,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "V: ",
            position=(30, 280),
        ),
        game_overlay_components.SpeedDialComponent(
            variable="VSpd",
            max_value=16.0,
            center=(160, 280),
            size=(180, 30),
        ),
        # game_overlay_components.SpeedDialComponentV2(
        #     variable="VSpd",
        #     max_value=16.0,
        #     center=(160, 280),
        #     size=(180, 30),
        # ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: f"{float(game_data.get('VSpd', 0.0)):8.4f}",
            position=(160, 305),
            align="middle",
            **SMALL_NUMBERS_CONFIG,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "S: ",
            position=(30, 340),
        ),
        game_overlay_components.SpeedDialComponent(
            variable="SdSpd",
            max_value=16.0,
            center=(160, 340),
            size=(180, 30),
        ),
        # game_overlay_components.SpeedDialComponentV2(
        #     variable="SdSpd",
        #     max_value=16.0,
        #     center=(160, 340),
        #     size=(180, 30),
        # ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: f"{float(game_data.get('SdSpd', 0.0)):8.4f}",
            position=(160, 365),
            align="middle",
            **SMALL_NUMBERS_CONFIG,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Global",
            position=(350, 160),
            align="middle",
        ),
        game_overlay_components.Speed2DPlaneComponent(
            x_variable="XSpd",
            y_variable="ZSpd",
            max_value=16.0,
            center=(350, 280),
            size=60,
            draw_axes=True,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Y",
            position=(450, 160),
            align="middle",
        ),
        game_overlay_components.SpeedDialComponent(
            variable="YSpd",
            max_value=16.0,
            center=(450, 280),
            size=(30, 120),
            orientation="vertical",
        ),
        # game_overlay_components.SpeedDialComponentV2(
        #     variable="YSpd",
        #     max_value=16.0,
        #     center=(450, 280),
        #     size=(30, 120),
        #     orientation="vertical",
        # ),
        # Position section
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Position",
            position=(30, 400),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "X:",
            position=(30, 460),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Y:",
            position=(30, 500),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Z:",
            position=(30, 540),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: f"{float(game_data.get('XPos', 0.0)):11.4f}",
            position=(60, 460),
            monospace=True,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: f"{float(game_data.get('YPos', 0.0)):11.4f}",
            position=(60, 500),
            monospace=True,
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda game_data: f"{float(game_data.get('ZPos', 0.0)):11.4f}",
            position=(60, 540),
            monospace=True,
        ),
        # Rotation section
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Rotation",
            position=(30, 600),
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Gravity Vector",
            position=(150, 650),
            align="middle",
        ),
        # TODO: Gravity direction
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Gravity Tilt",
            position=(350, 650),
            align="middle",
        ),
        game_overlay_components.GravityTiltComponent(
            x_rot_var="XRot",
            y_rot_var="YRot",
            z_rot_var="ZRot",
            center=(350, 730),
            size=PLOT_SIZE,
            draw_axes=False,
            method="vector",
        ),
        game_overlay_components.TextComponent(
            text_fn=lambda _: "Facing",
            position=(150, 820),
            align="middle",
        ),
        game_overlay_components.AngleDirectionComponent(
            variable="YRot",
            center=(150, 900),
            size=PLOT_SIZE,
            draw_axes=False,
        ),
        game_overlay_components.InputViewerComponent(
            center=(1200, 880),
            input_skin_name="TronStyleSA2B",
        ),
    ],
    resolution=(1960, 1080),
    game_feed_box=(480, 0, 1920, 1080),
)

import math

from .. import game_overlay, game_overlay_components

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

PLOT_SIZE = 50

SMALL_NUMBERS_CONFIG = {
    "monospace": False,
    "font_name_override": ["ArialBI.ttf", "Arimo-BoldItalic.ttf"],
    "font_size_override": 14,
    "font_color_override": WHITE,
    "font_stroke_width_override": 0,
}


def _character_select(game_data: dict) -> str | None:
    game_state = int(game_data["GameState"])
    character = int(game_data["CurrentCharacter"])

    if game_state in [7, 9, 16, 17]:
        if character == 7:
            return "eggman"
        elif character == 1:
            return "shadow"
        elif character == 5:
            return "rouge"
    return None


def _kart_select(game_data: dict) -> str | None:
    current_stage = int(game_data["CurrentStage"])

    if current_stage == 70:
        return "kart"
    else:
        return "nonkart"


def _rng_call(rng_state: int) -> int:
    return (rng_state * 0x41C64E6D + 0x3039) % 0x100000000


def _count_rng_calls(initial_rng_state: int, ending_rng_state: int):
    if initial_rng_state == ending_rng_state:
        return 0
    rng_state = initial_rng_state
    max_calls = 10000
    for i in range(max_calls):
        rng_state = _rng_call(rng_state)
        if rng_state == ending_rng_state:
            return i
    return max_calls


def _level_timer_in_frames(item: dict) -> int:
    return (
        int(item["StageCentiseconds"])
        + 60 * int(item["StageSeconds"])
        + 3600 * int(item["StageMinutes"])
    )


def _frames_to_timer(frames_count: int) -> tuple[int, int, int]:
    return (
        frames_count // 3600,
        (frames_count % 3600) // 60,
        math.ceil((frames_count % 60) * 100 / 60),
    )


def augment_game_data(game_data: game_overlay.GameOverlayData):
    for i in range(len(game_data.data)):
        item = game_data.data[i]
        if i == 0:
            item["LRTFrame"] = 0
            item["LRTMin"] = 0
            item["LRTSec"] = 0
            item["LRTCenti"] = 0
            item["RNGDeltaCalls"] = 0
            item["RNGCalls"] = 0
        else:
            prev_item = game_data.data[i - 1]
            level_timer = _level_timer_in_frames(item)
            prev_level_timer = _level_timer_in_frames(prev_item)
            if item["GameState"] == "17" or (
                item["GameState"] == "16" and level_timer > prev_level_timer
            ):
                item["LRTFrame"] = prev_item["LRTFrame"] + 1
            else:
                item["LRTFrame"] = prev_item["LRTFrame"]
            item["LRTMin"], item["LRTSec"], item["LRTCenti"] = _frames_to_timer(
                item["LRTFrame"]
            )
            item["RNGDeltaCalls"] = _count_rng_calls(
                int(prev_item["RNGState"]), int(item["RNGState"])
            )
            item["RNGCalls"] = item["RNGDeltaCalls"] + prev_item["RNGCalls"]


NON_KART_COMPONENTS = [
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
        selector=_character_select,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Time (LRT):",
        position=(30, 50),
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: (
            f"{int(game_data.get('LRTMin', '0')):02d}:{int(game_data.get('LRTSec', '0')):02d}:{int(game_data.get('LRTCenti', '0')):02d}"
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
        position=(30, 215),
    ),
    game_overlay_components.SpeedDialComponentV2(
        variable="FSpd",
        max_value=24.0,
        center=(160, 215),
        size=(180, 30),
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "V: ",
        position=(30, 260),
    ),
    game_overlay_components.SpeedDialComponentV2(
        variable="VSpd",
        max_value=24.0,
        center=(160, 260),
        size=(180, 30),
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "S: ",
        position=(30, 305),
    ),
    game_overlay_components.SpeedDialComponentV2(
        variable="SdSpd",
        max_value=24.0,
        center=(160, 305),
        size=(180, 30),
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "F:",
        position=(140, 330),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('FSpd', 0.0)):8.4f}",
        position=(170, 330),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "V:",
        position=(140, 345),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('VSpd', 0.0)):8.4f}",
        position=(170, 345),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "S:",
        position=(140, 360),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('SdSpd', 0.0)):8.4f}",
        position=(170, 360),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Global",
        position=(350, 160),
        align="middle",
    ),
    game_overlay_components.Speed2DPlaneComponent(
        x_variable="ZSpd",
        y_variable="XSpd",
        max_value=16.0,
        center=(350, 260),
        size=60,
        line_width_override=5,
        positive_x_label="+16",
        positive_y_label="+16",
        negative_x_label="-Z",
        negative_y_label="-X",
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
        center=(450, 260),
        size=(30, 120),
        orientation="vertical",
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "X:",
        position=(330, 330),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('XSpd', 0.0)):8.4f}",
        position=(360, 330),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Y:",
        position=(330, 345),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('YSpd', 0.0)):8.4f}",
        position=(360, 345),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Z:",
        position=(330, 360),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('ZSpd', 0.0)):8.4f}",
        position=(360, 360),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    # Position section
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Position",
        position=(150, 420),
        align="middle",
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "X:",
        position=(30, 470),
        font_size_override=24,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Y:",
        position=(30, 500),
        font_size_override=24,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Z:",
        position=(30, 530),
        font_size_override=24,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('XPos', 0.0)):11.4f}",
        position=(60, 470),
        monospace=True,
        font_size_override=24,
        font_monospace_gap_override=16,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('YPos', 0.0)):11.4f}",
        position=(60, 500),
        monospace=True,
        font_size_override=24,
        font_monospace_gap_override=16,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('ZPos', 0.0)):11.4f}",
        position=(60, 530),
        monospace=True,
        font_size_override=24,
        font_monospace_gap_override=16,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Facing Angle",
        position=(380, 420),
        align="middle",
    ),
    game_overlay_components.AngleDirectionComponent(
        variable="YRot",
        center=(380, 500),
        size=PLOT_SIZE,
        draw_axes=False,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "YRot:",
        position=(375, 565),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{int(game_data.get('YRot', 0)):05d}",
        position=(405, 565),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    # Rotation section
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Gravity Angle",
        position=(150, 620),
        align="middle",
    ),
    game_overlay_components.GravityAngleComponent(
        x_rot_var="XRot",
        y_rot_var="YRot",
        z_rot_var="ZRot",
        center=(150, 700),
        size=PLOT_SIZE,
        draw_axes=False,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "XRot:",
        position=(145, 765),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{int(game_data.get('XRot', 0)):05d}",
        position=(175, 765),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "ZRot:",
        position=(145, 780),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{int(game_data.get('ZRot', 0)):05d}",
        position=(175, 780),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Gravity Tilt",
        position=(380, 620),
        align="middle",
    ),
    game_overlay_components.GravityTiltGaugeComponent(
        x_rot_var="XRot",
        y_rot_var="YRot",
        z_rot_var="ZRot",
        center=(380, 700),
        size=PLOT_SIZE,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Action: {game_data['Action']}",
        position=(150, 850),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Hover: {game_data['Hover']}",
        position=(150, 880),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Total RNG Calls: {game_data['RNGCalls']}",
        position=(150, 910),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: (
            f"RNG Calls per Frame: {game_data['RNGDeltaCalls']}"
        ),
        position=(150, 940),
        font_size_override=20,
    ),
    game_overlay_components.InputViewerComponent(
        center=(1200, 950),
        input_skin_name="TronStyleSA2B",
    ),
    game_overlay_components.BlinkenlightComponent(
        variable="StatusBitfield",
        center=(350, 1010),
        size=PLOT_SIZE * 2,
        bit_color_override=[
            (0,250,0), None, None, None,
            None, None, None, None,
            None, None, (240, 160, 0), None,
            None, None, None, None,
        ],
        bit_inactive_color_override=(20,20,20),
    ),
]


KART_COMPONENTS = [
]


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
        axis_label_font_name=["ArialBI.ttf", "Arimo-BoldItalic.ttf"],
        axis_label_font_color=WHITE,
        axis_label_font_size=10,
        supersample_ratio=4,
    ),
    components=[
        game_overlay_components.LayoutSelector(
            position=(0, 0),
            size=(480, 1080),
            layouts={
                "nonkart": NON_KART_COMPONENTS,
                "kart": KART_COMPONENTS,
            },
            selector=_kart_select,
        ),
    ],
    resolution=(1920, 1080),
    game_feed_box=(480, 0, 1920, 1080),
)

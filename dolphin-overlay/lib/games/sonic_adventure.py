import math

from .. import game_overlay, game_overlay_components, math_utils

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


SMALL_NUMBERS_MONO_CONFIG = {
    "monospace": True,
    "font_monospace_gap_override": 8,
    "font_name_override": ["ArialBI.ttf", "Arimo-BoldItalic.ttf"],
    "font_size_override": 14,
    "font_color_override": WHITE,
    "font_stroke_width_override": 0,
}


def _character_select(game_data: dict) -> str | None:
    stage_map = {
        "0": None,
        "4": "shadow",
        "6": "shadow",
        "8": "rouge",
        "11": "eggman",
        "12": "eggman",
        "14": "shadow",
        "18": "rouge",
        "19": "shadow",
        "20": "eggman",
        "21": "eggman",
        "26": "rouge",
        "27": "eggman",
        "29": "eggman",
        "33": "rouge",
        "40": "shadow",
        "42": "shadow",
        "43": "eggman",
        "44": "rouge",
        "61": "shadow",
        "62": "rouge",
        "67": "eggman",
        "70": "rouge",
    }
    return stage_map.get(game_data["CurrentStage"])


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


def _unsigned_angle_to_bam(angle: int) -> int:
    angle %= 0x10000
    if angle > 0x7FFF:
        angle -= 0x10000
    return angle


def _signed_hex_format(value: int) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}0x{abs(value):04X} "


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
            if int(item["RNGState"]) == 0xDEAD0CAB:
                item["RNGDeltaCalls"] = 0
                item["RNGCalls"] = 0
            else:
                item["RNGDeltaCalls"] = _count_rng_calls(
                    int(prev_item["RNGState"]), int(item["RNGState"])
                )
                item["RNGCalls"] = item["RNGDeltaCalls"] + prev_item["RNGCalls"]

        x_rot = int(item["XRot"])
        y_rot = int(item["YRot"])
        z_rot = int(item["ZRot"])

        # generate a rotation from the incoming bcd values
        rot = math_utils.Rotation.from_bcd(x_rot, y_rot, z_rot)

        # make a global down vector and rotate it by our rotation to get our local down
        global_down = math_utils.Vector(0, -1, 0)
        local_down = global_down.rotate(rot)

        # find the angle of the tilt using local_down.y
        item["TiltAngle"] = math.asin(local_down.y) * 360 / math.tau

        item["KartDriftNeg"] = str(-int(item["KartDrift"]))
        item["KartZSpdNeg"] = str(-float(item["KartZSpd"]))
        item["KartHSpd"] = str(
            math.sqrt(float(item["KartZSpd"]) ** 2 + float(item["KartXSpd"]) ** 2)
        )


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
                game_overlay_components.TextComponent(
                    text_fn=lambda game_data: (
                        f"Ongoing Missiles: {game_data['NumberOngoingMissiles']}"
                    ),
                    position=(30, 950),
                    font_size_override=20,
                ),
                game_overlay_components.TextComponent(
                    text_fn=lambda game_data: (
                        f"Cannon Cooldown: {game_data['CannonShotCooldown']}"
                    ),
                    position=(30, 980),
                    font_size_override=20,
                ),
            ],
            "shadow": [
                game_overlay_components.StaticImageComponent(
                    image_filename="shadow.png",
                    position=(0, 0),
                    size=(480, 1080),
                ),
                game_overlay_components.TextComponent(
                    text_fn=lambda game_data: (
                        f"Spindash Charge: {game_data['SpindashCharge']}"
                    ),
                    position=(30, 950),
                    font_size_override=20,
                ),
                game_overlay_components.TextComponent(
                    text_fn=lambda game_data: (
                        f"Stored Speed: {float(game_data['StSpd']):8.4f}"
                    ),
                    position=(30, 980),
                    font_size_override=20,
                ),
            ],
            "rouge": [
                game_overlay_components.StaticImageComponent(
                    image_filename="rouge.png",
                    position=(0, 0),
                    size=(480, 1080),
                ),
                game_overlay_components.TextComponent(
                    text_fn=lambda game_data: (
                        f"Total RNG Calls: {game_data['RNGCalls']}"
                    ),
                    position=(30, 950),
                    font_size_override=20,
                ),
                game_overlay_components.TextComponent(
                    text_fn=lambda game_data: (
                        f"RNG Calls per Frame: {game_data['RNGDeltaCalls']}"
                    ),
                    position=(30, 980),
                    font_size_override=20,
                ),
            ],
        },
        default=[
            game_overlay_components.StaticImageComponent(
                image_filename="eggman.png",
                position=(0, 0),
                size=(480, 1080),
            ),
        ],
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
        softmax_value=16,
        hardmax_value=27.713,
        nonlinear=True,
        center=(160, 215),
        size=(180, 30),
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "V: ",
        position=(30, 260),
    ),
    game_overlay_components.SpeedDialComponentV2(
        variable="VSpd",
        softmax_value=16,
        hardmax_value=27.713,
        nonlinear=True,
        center=(160, 260),
        size=(180, 30),
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "S: ",
        position=(30, 305),
    ),
    game_overlay_components.SpeedDialComponentV2(
        variable="SdSpd",
        softmax_value=16,
        hardmax_value=27.713,
        nonlinear=True,
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
        position=(445, 160),
        align="middle",
    ),
    game_overlay_components.SpeedDialComponent(
        variable="YSpd",
        max_value=16.0,
        center=(445, 260),
        size=(30, 120),
        orientation="vertical",
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "X:",
        position=(315, 330),
        align="left",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('XSpd', 0.0)):8.4f}",
        position=(385, 330),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Y:",
        position=(315, 345),
        align="left",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('YSpd', 0.0)):8.4f}",
        position=(385, 345),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Z:",
        position=(315, 360),
        align="left",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('ZSpd', 0.0)):8.4f}",
        position=(385, 360),
        align="right",
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
        position=(330, 565),
        align="left",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: _signed_hex_format(
            _unsigned_angle_to_bam(int(game_data.get("YRot", 0)))
        ),
        position=(437, 565),
        align="right",
        **SMALL_NUMBERS_MONO_CONFIG,
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
        draw_axes=True,
        positive_x_label="+Z",
        positive_y_label="+X",
        negative_x_label="-Z",
        negative_y_label="-X",
        axis_rotation_variable="CameraYRot",
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "XRot:",
        position=(100, 765),
        align="left",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: _signed_hex_format(
            _unsigned_angle_to_bam(int(game_data.get("XRot", 0)))
        ),
        position=(207, 765),
        align="right",
        **SMALL_NUMBERS_MONO_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "ZRot:",
        position=(100, 780),
        align="left",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: _signed_hex_format(
            _unsigned_angle_to_bam(int(game_data.get("ZRot", 0)))
        ),
        position=(207, 780),
        align="right",
        **SMALL_NUMBERS_MONO_CONFIG,
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
        center=(358, 700),
        size=PLOT_SIZE,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data['TiltAngle']) + 90:.1f}°",
        position=(380, 765),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Action: {game_data['Action']}",
        position=(30, 850),
        font_size_override=28,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Hover: {game_data['Hover']}",
        position=(30, 890),
        font_size_override=28,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Status",
        position=(380, 855),
        align="middle",
    ),
    game_overlay_components.BlinkenlightComponent(
        variable="StatusBitfield",
        center=(380, 930),
        size=PLOT_SIZE * 2,
        bit_color_override=[
            (0x00, 0xfa, 0x00),
            (0xcc, 0x00, 0xff),
            (0xff, 0x00, 0x00),
            None,
            None,
            None,
            None,
            None,
            (0x00, 0xf6, 0xff),
            None,
            (0xf0, 0x7c, 0x00),
            None,
            None,
            (0x00, 0x84, 0xff),
            (0xff, 0xe4, 0x00),
            None,
        ],
        bit_inactive_color_override=(20, 20, 20),
    ),
]


KART_COMPONENTS = [
    # Background
    game_overlay_components.StaticImageComponent(
        image_filename="rouge.png",
        position=(0, 0),
        size=(480, 1080),
    ),
    # LRT timer
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
    # Local Speed
    game_overlay_components.TextComponent(
        text_fn=lambda _: "H Speed",
        position=(150, 125),
        align="middle",
    ),
    # game_overlay_components.SpeedDialComponentV2(
    #    variable="KartHSpd",
    #    max_value=20.0,
    #    center=(150, 260),
    #    size=(180, 30),
    # ),
    game_overlay_components.SpeedometerComponent(
        variable="KartHSpd",
        max_value=20.0,
        boost_variable="KartBoostTimer",
        center=(150, 260),
        background_image_path="speed.png",
        arrow_image_path="arrow.png",
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "H:",
        position=(125, 310),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"{float(game_data.get('KartHSpd', 0.0)):8.4f}",
        position=(155, 310),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    # Global Speed
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Global",
        position=(350, 160),
        align="middle",
    ),
    game_overlay_components.Speed2DPlaneComponent(
        x_variable="KartXSpd",
        y_variable="KartZSpdNeg",
        max_value=20.0,
        center=(350, 260),
        size=60,
        line_width_override=5,
        positive_x_label="+20",
        positive_y_label="-20",
        negative_x_label="-X",
        negative_y_label="+Z",
        draw_axes=True,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Y",
        position=(450, 160),
        align="middle",
    ),
    game_overlay_components.SpeedDialComponent(
        variable="KartYSpd",
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
        text_fn=lambda game_data: f"{float(game_data.get('KartXSpd', 0.0)):8.4f}",
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
        text_fn=lambda game_data: f"{float(game_data.get('KartYSpd', 0.0)):8.4f}",
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
        text_fn=lambda game_data: f"{float(game_data.get('KartZSpd', 0.0)):8.4f}",
        position=(360, 360),
        align="middle",
        **SMALL_NUMBERS_CONFIG,
    ),
    # Position
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
    # Drift Angle
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Drift Angle",
        position=(380, 420),
        align="middle",
    ),
    game_overlay_components.AngleDirectionComponent(
        variable="KartDriftNeg",
        center=(380, 500),
        size=PLOT_SIZE,
        draw_axes=False,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda _: "Drift Angle:",
        position=(390, 565),
        align="right",
        **SMALL_NUMBERS_CONFIG,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: _signed_hex_format(
            _unsigned_angle_to_bam(int(game_data.get("KartDrift", 0)))
        ),
        position=(452, 565),
        align="right",
        **SMALL_NUMBERS_MONO_CONFIG,
    ),
    # Extras
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Action: {game_data['KartState']}",
        position=(30, 850),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"Checkpoint: {game_data['KartCheckpoint']}",
        position=(30, 880),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"BoostPoints: {game_data['KartBoostPoints']}",
        position=(30, 910),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"BoostTimer: {game_data['KartBoostTimer']}",
        position=(30, 940),
        font_size_override=20,
    ),
    game_overlay_components.TextComponent(
        text_fn=lambda game_data: f"AirTime: {game_data['KartAirTime']}",
        position=(30, 970),
        font_size_override=20,
    ),
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
        game_overlay_components.InputViewerComponent(
            center=(1200, 950),
            input_skin_name="TronStyleSA2B",
        ),
    ],
    resolution=(1920, 1080),
    game_feed_box=(480, 0, 1920, 1080),
)

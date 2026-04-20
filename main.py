import math
import os
import random
import struct
import tempfile
import wave
import json
import sys
from dataclasses import dataclass

import pygame


WIDTH, HEIGHT = 1280, 720
GROUND_Y = HEIGHT - 110
FOREST_GROUND_Y = GROUND_Y + 52
FPS = 60
TITLE = "Dipper and Mabel in the Secret Bunker"

SKY = (18, 36, 44)
FOREST_DARK = (12, 24, 26)
FOREST_MID = (32, 65, 52)
FOREST_LIGHT = (75, 122, 94)
AMBER = (255, 209, 102)
PAPER = (237, 229, 193)
CRIMSON = (191, 58, 69)
CYAN = (113, 219, 255)
STONE = (74, 77, 104)
MIST = (194, 219, 214)
BLACK = (16, 14, 20)
WHITE = (245, 244, 232)

FOREST_LAYER_OVERRIDES = {
    1: {"speed": 0.05, "scale": 1.25, "offset_y": -175},
    2: {"speed": 0.08, "scale": 1.25, "offset_y": -175},
    3: {"speed": 0.11, "scale": 1.25, "offset_y": -175},
    4: {"speed": 0.14, "scale": 1.25, "offset_y": -175},
    5: {"speed": 0.18, "scale": 1.25, "offset_y": -175},
    6: {"speed": 0.22, "scale": 1.25, "offset_y": -175},
    7: {"speed": 0.27, "scale": 1.25, "offset_y": -175},
    8: {"speed": 0.33, "scale": 1.25, "offset_y": -175},
    9: {"speed": 0.40, "scale": 1.25, "offset_y": -175},
    10: {"speed": 0.48, "scale": 1.25, "offset_y": -175},
    11: {"speed": 0.57, "scale": 1.25, "offset_y": -175},
    12: {"speed": 0.67, "scale": 1.25, "offset_y": -175},
}

BUNKER_LAYER_OVERRIDES = {
    1: {"speed": 0.04, "scale": 1.02, "offset_y": -18},
    2: {"speed": 0.07, "scale": 1.02, "offset_y": -18},
    3: {"speed": 0.10, "scale": 1.02, "offset_y": -18},
    4: {"speed": 0.14, "scale": 1.02, "offset_y": -18},
    5: {"speed": 0.18, "scale": 1.02, "offset_y": -18},
    6: {"speed": 0.23, "scale": 1.02, "offset_y": -18},
    7: {"speed": 0.28, "scale": 1.02, "offset_y": -18},
    8: {"speed": 0.34, "scale": 1.02, "offset_y": -18},
    9: {"speed": 0.41, "scale": 1.02, "offset_y": -18},
    10: {"speed": 0.49, "scale": 1.02, "offset_y": -18},
    11: {"speed": 0.58, "scale": 1.02, "offset_y": -18},
    12: {"speed": 0.68, "scale": 1.02, "offset_y": -18},
}

PARALLAX_IMAGE_CACHE = {}
TILESET_CACHE = {}
SFX_SOUNDS = {}

APP_DIR = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
SAVE_FILE = os.path.join(APP_DIR, "savegame.json")


def clamp(value, low, high):
    return max(low, min(high, value))


def can_land_on_one_way_platform(previous_rect, current_rect, platform_rect, velocity_y):
    return (
        velocity_y >= 0
        and previous_rect.bottom <= platform_rect.top
        and current_rect.bottom >= platform_rect.top
    )


def is_flashlight_pressed(keys):
    mouse_buttons = pygame.mouse.get_pressed(3)
    return keys[pygame.K_f] or mouse_buttons[0]


def ease(value):
    value = clamp(value, 0.0, 1.0)
    return value * value * (3 - 2 * value)


def first_existing(*paths):
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def load_scaled_image(path, size):
    if not path:
        return None
    try:
        image = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(image, size)
    except pygame.error:
        return None


def synth_sfx(name):
    sample_rate = 22050
    duration_map = {
        "jump": 0.12,
        "page": 0.18,
        "hit": 0.16,
        "cipher_open": 0.2,
        "cipher_solve": 0.42,
        "burn": 0.24,
        "boss_teleport": 0.28,
        "boss_attack": 0.18,
        "portal": 0.3,
        "menu": 0.09,
    }
    seconds = duration_map.get(name, 0.16)
    path = os.path.join(tempfile.gettempdir(), f"gravityfalls_{name}.wav")
    if os.path.exists(path):
        return path

    frames = []
    total_frames = int(sample_rate * seconds)
    for index in range(total_frames):
        t = index / sample_rate
        env = max(0.0, 1.0 - (t / seconds))
        env *= env
        sample = 0.0
        if name == "jump":
            freq = 560 - 260 * (t / seconds)
            sample = math.sin(2 * math.pi * freq * t) * env * 0.5
        elif name == "page":
            freq = 820 + 180 * math.sin(t * 28)
            sample = (math.sin(2 * math.pi * freq * t) + 0.4 * math.sin(2 * math.pi * freq * 1.5 * t)) * env * 0.32
        elif name == "hit":
            noise = (random.random() * 2 - 1) * 0.7
            tone = math.sin(2 * math.pi * 160 * t) * 0.18
            sample = (noise + tone) * env * 0.42
        elif name == "cipher_open":
            freq = 380 + 140 * (t / seconds)
            sample = (math.sin(2 * math.pi * freq * t) + 0.5 * math.sin(2 * math.pi * (freq * 1.98) * t)) * env * 0.32
        elif name == "cipher_solve":
            base = 420 + 110 * math.sin(t * 10)
            sample = (
                math.sin(2 * math.pi * base * t)
                + 0.55 * math.sin(2 * math.pi * base * 1.5 * t + 0.4)
                + 0.25 * math.sin(2 * math.pi * base * 2.1 * t)
            ) * env * 0.28
        elif name == "burn":
            noise = (random.random() * 2 - 1) * 0.5
            tone = math.sin(2 * math.pi * (240 + t * 420) * t) * 0.25
            sample = (noise * 0.7 + tone) * env * 0.36
        elif name == "boss_teleport":
            freq = 260 - 120 * (t / seconds)
            sample = (
                math.sin(2 * math.pi * freq * t)
                + 0.45 * math.sin(2 * math.pi * freq * 0.5 * t + 0.8)
                + (random.random() * 2 - 1) * 0.18
            ) * env * 0.4
        elif name == "boss_attack":
            freq = 170 + 50 * math.sin(t * 24)
            sample = (
                math.sin(2 * math.pi * freq * t)
                + 0.3 * math.sin(2 * math.pi * freq * 3.0 * t)
                + (random.random() * 2 - 1) * 0.08
            ) * env * 0.34
        elif name == "portal":
            freq = 260 + 240 * (t / seconds)
            sample = (
                math.sin(2 * math.pi * freq * t)
                + 0.4 * math.sin(2 * math.pi * freq * 2.0 * t + 0.4)
            ) * env * 0.28
        elif name == "menu":
            freq = 720 + 110 * (t / seconds)
            sample = math.sin(2 * math.pi * freq * t) * env * 0.22
        value = int(clamp(sample, -1.0, 1.0) * 32767)
        frames.append(struct.pack("<hh", value, value))

    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))
    return path


def load_sfx_sound(name, volume=0.5):
    if not pygame.mixer.get_init():
        return None
    try:
        sound = pygame.mixer.Sound(synth_sfx(name))
        sound.set_volume(volume)
        return sound
    except pygame.error:
        return None


def play_sfx(name):
    sound = SFX_SOUNDS.get(name)
    if sound is not None:
        try:
            sound.play()
        except pygame.error:
            pass


def load_image(path):
    if not path:
        return None
    try:
        return pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None


def trim_transparent_bounds(image):
    if image is None:
        return None
    bounds = image.get_bounding_rect(min_alpha=1)
    if bounds.width <= 0 or bounds.height <= 0:
        return image
    return image.subsurface(bounds).copy()


def crop_visible_bounds(image, min_alpha=20):
    if image is None:
        return None
    bounds = image.get_bounding_rect(min_alpha=min_alpha)
    if bounds.width <= 0 or bounds.height <= 0:
        return image
    return image.subsurface(bounds).copy()


def fit_size(source_size, target_size):
    src_w, src_h = source_size
    dst_w, dst_h = target_size
    if src_w <= 0 or src_h <= 0:
        return target_size
    scale = min(dst_w / src_w, dst_h / src_h)
    return max(1, int(src_w * scale)), max(1, int(src_h * scale))


def scale_to_rect(image, size):
    if image is None:
        return None
    return pygame.transform.smoothscale(image, size)


def mix_color(color_a, color_b, blend):
    blend = clamp(blend, 0.0, 1.0)
    return tuple(int(color_a[i] * (1 - blend) + color_b[i] * blend) for i in range(3))


def shift_color(color, amount):
    return tuple(clamp(channel + amount, 0, 255) for channel in color)


def draw_forest_ground(surface, top_y, camera_x):
    rect = pygame.Rect(0, top_y, WIDTH, HEIGHT - top_y)
    base = (42, 66, 44)
    mid = (57, 83, 52)
    shadow = (30, 48, 31)
    moss = (94, 124, 72)
    root = (66, 52, 34)
    stone = (82, 88, 66)

    pygame.draw.rect(surface, base, rect)
    pygame.draw.rect(surface, mid, (0, top_y, WIDTH, 22))
    pygame.draw.rect(surface, shadow, (0, top_y + 22, WIDTH, 18))

    tick = pygame.time.get_ticks()
    for x in range(-24, WIDTH + 48, 46):
        drift = int((camera_x * 0.35 + x * 0.3) % 46)
        blade_x = x - drift
        blade_h = 8 + ((x // 23) % 8)
        pygame.draw.line(surface, moss, (blade_x, top_y + 4), (blade_x + 3, top_y - blade_h), 2)
        pygame.draw.line(surface, shift_color(moss, -18), (blade_x + 6, top_y + 5), (blade_x + 8, top_y - blade_h + 2), 2)

    for x in range(-40, WIDTH + 80, 74):
        root_x = x - int(camera_x * 0.5) % 74
        root_width = 18 + (x // 37) % 12
        pygame.draw.ellipse(surface, root, (root_x, top_y + 10, root_width, 10))

    for x in range(-20, WIDTH + 40, 54):
        stone_x = x - int(camera_x * 0.22) % 54
        stone_y = top_y + 26 + ((x // 27) % 4) * 10
        stone_w = 10 + (x // 17) % 7
        pygame.draw.ellipse(surface, stone, (stone_x, stone_y, stone_w, 6))
        pygame.draw.ellipse(surface, shift_color(stone, -16), (stone_x + 2, stone_y + 2, max(4, stone_w - 4), 3))

    for y in range(top_y + 46, HEIGHT, 24):
        band = mix_color(base, shadow, min(1.0, (y - top_y) / max(1, HEIGHT - top_y)))
        pygame.draw.line(surface, band, (0, y), (WIDTH, y))

    for x in range(-30, WIDTH + 60, 64):
        root_x = x - int(camera_x * 0.4) % 64
        root_len = 18 + (x // 31) % 18
        pygame.draw.line(surface, shift_color(root, -6), (root_x, top_y + 28), (root_x - 6, top_y + 28 + root_len), 2)
        pygame.draw.line(surface, shift_color(root, 8), (root_x + 10, top_y + 24), (root_x + 14, top_y + 18 + root_len), 2)

    haze = pygame.Surface((WIDTH, max(1, HEIGHT - top_y)), pygame.SRCALPHA)
    haze.fill((255, 231, 181, 10 + int(6 * math.sin(tick * 0.0015))))
    surface.blit(haze, (0, top_y))


def draw_stone_surface(surface, rect, palette, camera_x=0, border_radius=6):
    top = palette["top"]
    mid = palette["mid"]
    shadow = palette["shadow"]
    crack = palette["crack"]
    highlight = palette["highlight"]
    accent = palette.get("accent", highlight)

    pygame.draw.rect(surface, mid, rect, border_radius=border_radius)
    top_band_h = max(8, rect.height // 3)
    pygame.draw.rect(surface, top, (rect.x, rect.y, rect.width, top_band_h), border_radius=border_radius)
    pygame.draw.rect(surface, shadow, (rect.x, rect.bottom - max(6, rect.height // 4), rect.width, max(6, rect.height // 4)), border_radius=border_radius)

    for x in range(rect.x - 20, rect.right + 20, 34):
        seam_x = x - int(camera_x * 0.18) % 34
        pygame.draw.line(surface, shift_color(mid, -12), (seam_x, rect.y + 4), (seam_x + 6, rect.bottom - 5), 1)

    for x in range(rect.x + 10, rect.right - 10, 42):
        pebble_y = rect.y + top_band_h + ((x // 21) % 3) * 5
        pygame.draw.ellipse(surface, accent, (x - int(camera_x * 0.12) % 18, pebble_y, 12, 5))

    crack_start = rect.x + 18 - int(camera_x * 0.1) % 24
    for x in range(crack_start, rect.right - 18, 46):
        points = [
            (x, rect.y + top_band_h - 2),
            (x + 6, rect.y + top_band_h + 6),
            (x - 2, rect.y + top_band_h + 12),
            (x + 10, rect.bottom - 8),
        ]
        pygame.draw.lines(surface, crack, False, points, 2)

    pygame.draw.line(surface, highlight, (rect.x + 4, rect.y + 3), (rect.right - 4, rect.y + 3), 2)
    pygame.draw.line(surface, shift_color(shadow, -10), (rect.x + 4, rect.bottom - 3), (rect.right - 4, rect.bottom - 3), 2)


def draw_tiled_surface(surface, rect, tile_image, border_radius=6, overlay_color=None, border_color=None):
    if tile_image is None:
        return
    if rect.width <= 0 or rect.height <= 0:
        return
    cache_key = (id(tile_image), 64)
    tile = TILESET_CACHE.get(cache_key)
    if tile is None:
        source = crop_visible_bounds(tile_image, min_alpha=1) or tile_image
        tile = pygame.transform.smoothscale(source, (64, 64))
        TILESET_CACHE[cache_key] = tile

    temp = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y in range(0, rect.height, tile.get_height()):
        for x in range(0, rect.width, tile.get_width()):
            temp.blit(tile, (x, y))
    if overlay_color:
        temp.fill(overlay_color, special_flags=pygame.BLEND_RGBA_MULT)
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=border_radius)
    temp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(temp, rect.topleft)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=border_radius)


def draw_flashlight_beam(surface, origin, facing, active=True):
    if not active:
        return
    tick = pygame.time.get_ticks()
    flicker = 0.96 + 0.04 * math.sin(tick * 0.008)
    beam_w = 238
    beam_h = 132
    beam = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)

    center_y = beam_h / 2
    gradient = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
    for x in range(beam_w):
        along = x / max(1, beam_w - 1)
        spread = 10 + along * 34
        softness = 0.7 + along * 0.3
        alpha = int((1.0 - along) ** 2.2 * 26 * flicker)
        if alpha <= 0:
            continue
        top = int(center_y - spread * softness)
        bottom = int(center_y + spread * softness)
        pygame.draw.line(gradient, (255, 244, 220, alpha), (x, top), (x, bottom))
    beam.blit(gradient, (0, 0))

    # Keep only a very soft core so the beam guides the eye without covering the scene.
    core = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
    for x in range(beam_w):
        along = x / max(1, beam_w - 1)
        spread = 6 + along * 18
        alpha = int((1.0 - along) ** 2.45 * 18 * flicker)
        if alpha <= 0:
            continue
        pygame.draw.line(
            core,
            (255, 250, 238, alpha),
            (x, int(center_y - spread)),
            (x, int(center_y + spread)),
        )
    beam.blit(core, (0, 0))

    dust = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
    for index in range(5):
        px = 46 + index * 32 + int(5 * math.sin(tick * 0.002 + index))
        py = 30 + (index * 17) % (beam_h - 60)
        radius = 1 + (index % 2)
        pygame.draw.circle(dust, (255, 245, 225, 8), (px, py), radius)
    beam.blit(dust, (0, 0))

    if facing < 0:
        beam = pygame.transform.flip(beam, True, False)

    beam_rect = beam.get_rect()
    if facing > 0:
        beam_rect.midleft = (origin[0] - 4, origin[1])
    else:
        beam_rect.midright = (origin[0] + 4, origin[1])
    surface.blit(beam, beam_rect.topleft)

    glow = pygame.Surface((40, 40), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 223, 150, int(24 * flicker)), (20, 20), 12)
    pygame.draw.circle(glow, (255, 243, 214, int(38 * flicker)), (20, 20), 5)
    glow_rect = glow.get_rect(center=origin)
    surface.blit(glow, glow_rect.topleft)


def draw_level_background(surface, image, camera_x=0, max_camera=0):
    if image is None:
        return False
    image_w, image_h = image.get_size()
    if image_h != HEIGHT:
        scale = HEIGHT / max(1, image_h)
        image_w = max(1, int(image_w * scale))
        image = pygame.transform.smoothscale(image, (image_w, HEIGHT))
    if image_w <= WIDTH:
        x = (WIDTH - image_w) // 2
        surface.blit(image, (x, 0))
        return True
    extra_width = image_w - WIDTH
    if max_camera > 0:
        offset_x = int(extra_width * clamp(camera_x / max_camera, 0.0, 1.0))
    else:
        offset_x = extra_width // 2
    surface.blit(image, (-offset_x, 0))
    return True


def load_parallax_layers(prefix, count=12):
    layers = []
    for index in range(1, count + 1):
        path = first_existing(
            os.path.join(IMAGES_DIR, f"{prefix}_layer_{index}.png"),
            os.path.join(IMAGES_DIR, f"{prefix}_layer_{index}.jpg"),
            os.path.join(IMAGES_DIR, f"{prefix}_layer_{index}_auto.png"),
            os.path.join(IMAGES_DIR, f"{prefix}_layer_{index}_auto.jpg"),
            os.path.join(ASSETS_DIR, f"{prefix}_layer_{index}.png"),
            os.path.join(ASSETS_DIR, f"{prefix}_layer_{index}.jpg"),
            os.path.join(ASSETS_DIR, f"{prefix}_layer_{index}_auto.png"),
            os.path.join(ASSETS_DIR, f"{prefix}_layer_{index}_auto.jpg"),
        )
        if path:
            # Keep the original canvas size for parallax layers so all exported
            # pieces preserve their shared alignment when composited together.
            layers.append(load_image(path))
    return [layer for layer in layers if layer is not None]


def load_numbered_layer_stack(base_name="Layer", start=0, end=9):
    layers = []
    for index in range(start, end + 1):
        path = first_existing(
            os.path.join(IMAGES_DIR, f"{base_name}_{index}.png"),
            os.path.join(IMAGES_DIR, f"{base_name}_{index}.jpg"),
            os.path.join(IMAGES_DIR, f"{base_name}_{index}.jpeg"),
            os.path.join(IMAGES_DIR, f"{base_name}_0_{index}.png"),
            os.path.join(IMAGES_DIR, f"{base_name}_0_{index}.jpg"),
            os.path.join(IMAGES_DIR, f"{base_name}_1_{index}.png"),
            os.path.join(IMAGES_DIR, f"{base_name}_1_{index}.jpg"),
        )
        if path:
            layers.append(load_image(path))
    return [layer for layer in layers if layer is not None]


def draw_parallax_layers(surface, layers, camera_x=0, max_camera=0, overrides=None):
    if not layers:
        return False
    layer_count = len(layers)
    for index, layer in enumerate(layers):
        layer_number = index + 1
        config = overrides.get(layer_number, {}) if overrides else {}
        factor = config.get("speed", 0.12 + (0.88 * index / max(1, layer_count - 1)))
        custom_scale = config.get("scale", 1.0)
        cache_key = (id(layer), custom_scale)
        cached = PARALLAX_IMAGE_CACHE.get(cache_key)
        if cached is None:
            image = layer
            image_w, image_h = image.get_size()
            base_scale = min(WIDTH / max(1, image_w), HEIGHT / max(1, image_h))
            image_w = max(1, round(image_w * base_scale))
            image_h = max(1, round(image_h * base_scale))
            image = pygame.transform.smoothscale(image, (image_w, image_h))
            if custom_scale != 1.0:
                image_w = max(1, round(image_w * custom_scale))
                image_h = max(1, round(image_h * custom_scale))
                image = pygame.transform.smoothscale(image, (image_w, image_h))
            cached = (image, image_w, image_h)
            PARALLAX_IMAGE_CACHE[cache_key] = cached
        image, image_w, image_h = cached
        if image_w <= 0:
            continue
        base_x = (WIDTH - image_w) // 2 if config.get("center_x") else 0
        base_y = config.get("offset_y", 0)
        if config.get("repeat", True):
            offset_x = round(camera_x * factor) % image_w
            draw_x = base_x - offset_x
            while draw_x < WIDTH:
                surface.blit(image, (draw_x, base_y))
                draw_x += image_w
        else:
            draw_x = round(base_x - camera_x * factor)
            surface.blit(image, (draw_x, base_y))
    return True


def load_font(path, size, fallback_name, bold=False):
    try:
        if path and os.path.exists(path):
            return pygame.font.Font(path, size)
    except pygame.error:
        pass
    return pygame.font.SysFont(fallback_name, size, bold=bold)


def make_music():
    sample_rate = 22050
    seconds = 18
    path = os.path.join(tempfile.gettempdir(), "gravity_falls_indie_folk_loop.wav")
    if os.path.exists(path):
        return path

    notes = {
        "A2": 110.00,
        "C3": 130.81,
        "D3": 146.83,
        "E3": 164.81,
        "G3": 196.00,
        "A3": 220.00,
        "C4": 261.63,
        "D4": 293.66,
        "E4": 329.63,
        "G4": 392.00,
    }
    progression = [
        ("A2", "E3", "A3", "C4"),
        ("C3", "G3", "C4", "E4"),
        ("D3", "A3", "D4", "E4"),
        ("E3", "G3", "D4", "G4"),
    ]

    frames = []
    total_frames = sample_rate * seconds
    random.seed(42)
    for index in range(total_frames):
        t = index / sample_rate
        beat = int(t * 2) % len(progression)
        chord = progression[beat]
        local = t % 0.5
        attack = math.exp(-8.0 * local)
        trem = 0.85 + 0.15 * math.sin(t * 0.9)

        signal = 0.0
        for offset, note in enumerate(chord):
            freq = notes[note]
            detune = 1.0 + offset * 0.0025
            signal += math.sin(2 * math.pi * freq * detune * t)
            signal += 0.35 * math.sin(2 * math.pi * freq * 2 * t + 0.1 * offset)
            signal += 0.12 * math.sin(2 * math.pi * freq * 3 * t + 0.2 * offset)
        signal *= 0.14 * attack * trem

        pad = 0.09 * math.sin(2 * math.pi * 55 * t)
        pad += 0.06 * math.sin(2 * math.pi * 82.4 * t + 0.7)
        suspense = 0.05 * math.sin(2 * math.pi * (180 + 30 * math.sin(t * 0.35)) * t)
        tension = ease((t - 6) / 10.5) * suspense
        tape = (random.random() * 2 - 1) * 0.018
        wobble = 1 + 0.003 * math.sin(t * 1.1) + 0.002 * math.sin(t * 0.37)
        sample = (signal + pad * wobble + tension + tape) * 0.8
        sample = clamp(sample, -1.0, 1.0)
        value = int(sample * 32767)
        frames.append(struct.pack("<hh", value, value))

    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))
    return path


@dataclass
class FloatText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: float = 1.4

    def update(self, dt):
        self.life -= dt
        self.y -= 35 * dt
        return self.life > 0


class Player:
    sprites = {"idle": None, "run": []}

    def __init__(self):
        self.rect = pygame.Rect(120, GROUND_Y - 78, 42, 78)
        self.vel = pygame.Vector2()
        self.speed = 520
        self.jump_strength = -650
        self.on_ground = False
        self.health = 5
        self.max_health = 5
        self.facing = 1
        self.invuln = 0.0
        self.reveal_energy = 5.5
        self.max_reveal = 5.5
        self.reveal_active = False
        self.portal_charge = 0.0
        self.is_moving = False
        self.run_anim_time = 0.0

    @classmethod
    def set_sprites(cls, idle_sprite=None, run_sprites=None):
        cls.sprites = {
            "idle": trim_transparent_bounds(idle_sprite),
            "run": [trim_transparent_bounds(sprite) for sprite in (run_sprites or []) if sprite is not None],
        }

    def reset_position(self, x, y):
        self.rect.topleft = (x, y)
        self.vel.update(0, 0)
        self.on_ground = False
        self.invuln = 0.0
        self.portal_charge = 0.0
        self.is_moving = False
        self.run_anim_time = 0.0

    def set_motion_state(self, moving, dt):
        self.is_moving = moving
        if moving:
            self.run_anim_time += dt
        else:
            self.run_anim_time = 0.0

    def apply_damage(self, amount=1):
        if self.invuln > 0:
            return False
        self.health -= amount
        self.invuln = 1.1
        return True

    def update_common(self, dt):
        if self.invuln > 0:
            self.invuln -= dt
        if self.reveal_active:
            self.reveal_energy = max(0.0, self.reveal_energy - dt * 1.35)
        else:
            self.reveal_energy = min(self.max_reveal, self.reveal_energy + dt * 0.75)
        if self.reveal_energy <= 0.05:
            self.reveal_active = False

    def draw(self, surface, camera_x=0, shake=0):
        sprite_pack = Player.sprites
        run_sprites = sprite_pack["run"]
        sprite = sprite_pack["idle"]
        if self.is_moving and run_sprites:
            frame_index = int(self.run_anim_time * 1.4) % len(run_sprites)
            sprite = run_sprites[frame_index]
        if sprite:
            draw_sprite = pygame.transform.flip(sprite, self.facing < 0, False)
            target_size = fit_size(draw_sprite.get_size(), (88, 112))
            scaled = pygame.transform.smoothscale(draw_sprite, target_size)
            draw_x = round(self.rect.centerx - camera_x - scaled.get_width() / 2 + shake)
            draw_y = round(self.rect.bottom - scaled.get_height() + shake * 0.1)
            if self.invuln > 0 and int(self.invuln * 14) % 2 == 0:
                flashed = scaled.copy()
                flashed.fill((255, 255, 255, 105), special_flags=pygame.BLEND_RGBA_ADD)
                scaled = flashed
            surface.blit(scaled, (draw_x, draw_y))
            if self.reveal_active:
                beam_origin = (
                    draw_x + scaled.get_width() - 6 if self.facing > 0 else draw_x + 6,
                    draw_y + 34,
                )
                draw_flashlight_beam(surface, beam_origin, self.facing, True)
            return

        x = self.rect.x - camera_x + shake
        y = self.rect.y + shake * 0.1
        flash = self.invuln > 0 and int(self.invuln * 14) % 2 == 0
        shirt = (54, 140, 224) if not flash else WHITE

        pygame.draw.rect(surface, (40, 30, 30), (x + 12, y + 12, 18, 14), border_radius=8)
        pygame.draw.rect(surface, shirt, (x + 8, y + 24, 26, 30), border_radius=6)
        pygame.draw.rect(surface, (82, 48, 26), (x + 6, y + 54, 12, 24), border_radius=4)
        pygame.draw.rect(surface, (82, 48, 26), (x + 24, y + 54, 12, 24), border_radius=4)
        pygame.draw.rect(surface, (238, 203, 169), (x + 10, y + 6, 22, 20), border_radius=10)

        hat = [(x + 5, y + 14), (x + 34, y + 14), (x + 28, y), (x + 12, y)]
        pygame.draw.polygon(surface, (24, 42, 85), hat)
        pygame.draw.rect(surface, (40, 67, 121), (x + 6, y + 12, 28, 6), border_radius=3)
        eye_x = x + (24 if self.facing > 0 else 16)
        pygame.draw.circle(surface, BLACK, (eye_x, y + 16), 2)

        if self.reveal_active:
            beam_origin = (x + 28 if self.facing > 0 else x + 6, y + 34)
            draw_flashlight_beam(surface, beam_origin, self.facing, True)


class GnomeSprite:
    sprites = {"idle": None, "run": []}
    palette = {
        "skin": (234, 204, 178),
        "nose": (220, 154, 126),
        "beard": (244, 242, 232),
        "beard_shade": (198, 198, 196),
        "tunic": (78, 106, 74),
        "tunic_light": (112, 144, 102),
        "belt": (92, 58, 31),
        "boot": (56, 42, 34),
        "hat": (176, 32, 36),
        "hat_light": (220, 70, 76),
        "gold": (226, 188, 96),
        "outline": (30, 22, 20),
        "lantern": (246, 214, 126),
        "glow": (255, 226, 148, 78),
        "eye": (18, 18, 22),
    }

    @classmethod
    def set_sprites(cls, idle_sprite=None, run_sprites=None):
        run = [trim_transparent_bounds(sprite) for sprite in (run_sprites or []) if sprite is not None]
        idle = trim_transparent_bounds(idle_sprite)
        if idle is None and run:
            idle = run[0]
        cls.sprites = {
            "idle": idle,
            "run": run or cls.generate_default_frames()[1:],
        }
        if cls.sprites["idle"] is None:
            cls.sprites["idle"] = cls.generate_default_frames()[0]

    @classmethod
    def generate_default_frames(cls):
        steps = [
            (2, 0, False),
            (0, 1, False),
            (1, 0, False),
            (2, -1, True),
            (3, 0, False),
        ]
        return [cls.build_frame(step, bob, blink) for step, bob, blink in steps]

    @classmethod
    def build_frame(cls, step, bob=0, blink=False):
        colors = cls.palette
        width, height = 76, 66
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        base_y = 10 + bob

        glow = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(glow, colors["glow"], (16, 16), 16)
        surface.blit(glow, (42, base_y + 18))
        pygame.draw.ellipse(surface, (0, 0, 0, 58), (16, 55 + bob, 42, 8))

        pygame.draw.polygon(surface, colors["hat"], [(16, base_y + 15), (30, base_y - 6), (46, base_y + 13), (41, base_y + 19), (22, base_y + 19)])
        pygame.draw.rect(surface, colors["hat"], (16, base_y + 15, 30, 6), border_radius=3)
        pygame.draw.rect(surface, colors["hat_light"], (23, base_y + 2, 7, 10), border_radius=2)
        pygame.draw.circle(surface, colors["gold"], (42, base_y + 9), 3)

        pygame.draw.circle(surface, colors["skin"], (31, base_y + 24), 11)
        pygame.draw.circle(surface, colors["nose"], (37, base_y + 27), 4)
        eye_y = base_y + 22
        if blink:
            pygame.draw.line(surface, colors["eye"], (24, eye_y), (28, eye_y), 2)
        else:
            pygame.draw.circle(surface, colors["eye"], (25, eye_y), 2)
        pygame.draw.circle(surface, colors["eye"], (31, eye_y + 1), 1)
        pygame.draw.line(surface, colors["eye"], (21, eye_y - 4), (27, eye_y - 6), 1)
        pygame.draw.line(surface, colors["eye"], (29, eye_y - 5), (34, eye_y - 7), 1)

        pygame.draw.polygon(surface, colors["beard"], [(18, base_y + 28), (41, base_y + 28), (48, base_y + 44), (31, base_y + 55), (13, base_y + 44)])
        pygame.draw.line(surface, colors["beard_shade"], (31, base_y + 30), (31, base_y + 51), 2)
        pygame.draw.line(surface, colors["beard_shade"], (25, base_y + 34), (21, base_y + 45), 2)
        pygame.draw.line(surface, colors["beard_shade"], (37, base_y + 34), (41, base_y + 45), 2)

        pygame.draw.rect(surface, colors["tunic"], (18, base_y + 33, 26, 16), border_radius=6)
        pygame.draw.rect(surface, colors["tunic_light"], (22, base_y + 36, 18, 6), border_radius=3)
        pygame.draw.rect(surface, colors["belt"], (19, base_y + 43, 24, 4), border_radius=2)
        pygame.draw.rect(surface, colors["gold"], (29, base_y + 42, 5, 6), border_radius=2)

        arm_y = base_y + 36 + (1 if step in (1, 2) else 0)
        pygame.draw.line(surface, colors["skin"], (41, base_y + 36), (50, arm_y + 3), 4)
        pygame.draw.line(surface, colors["outline"], (51, arm_y + 5), (51, arm_y + 13), 2)
        pygame.draw.rect(surface, (88, 70, 46), (46, arm_y + 10, 10, 12), border_radius=2)
        pygame.draw.rect(surface, colors["lantern"], (48, arm_y + 12, 6, 6), border_radius=2)

        arm_offset = -2 if step in (0, 3) else 2
        pygame.draw.line(surface, colors["tunic_light"], (18, base_y + 36), (11, base_y + 38 + arm_offset), 4)

        leg_specs = [(-4, 4), (4, -4), (2, -2), (-2, 2)]
        left_dx, right_dx = leg_specs[step % len(leg_specs)]
        hip_y = base_y + 47
        pygame.draw.line(surface, colors["boot"], (27, hip_y), (25 + left_dx, base_y + 59), 5)
        pygame.draw.line(surface, colors["boot"], (35, hip_y), (37 + right_dx, base_y + 59), 5)
        pygame.draw.line(surface, colors["boot"], (21 + left_dx, base_y + 60), (29 + left_dx, base_y + 60), 4)
        pygame.draw.line(surface, colors["boot"], (33 + right_dx, base_y + 60), (41 + right_dx, base_y + 60), 4)

        pygame.draw.lines(surface, colors["outline"], False, [(20, base_y + 19), (17, base_y + 15), (30, base_y - 5), (45, base_y + 13)], 1)
        pygame.draw.arc(surface, colors["outline"], (18, base_y + 14, 26, 20), math.pi, math.tau, 1)
        pygame.draw.line(surface, colors["outline"], (18, base_y + 28), (14, base_y + 44), 1)
        pygame.draw.line(surface, colors["outline"], (41, base_y + 28), (46, base_y + 44), 1)
        pygame.draw.line(surface, colors["outline"], (23, base_y + 33), (23, base_y + 45), 1)
        pygame.draw.line(surface, colors["outline"], (39, base_y + 33), (39, base_y + 45), 1)
        return trim_transparent_bounds(surface)

    @classmethod
    def draw(cls, surface, rect, anim_time=0.0):
        sprite_pack = cls.sprites
        run_sprites = sprite_pack["run"]
        sprite = sprite_pack["idle"]
        if run_sprites:
            frame_index = int(anim_time * 1.8) % len(run_sprites)
            sprite = run_sprites[frame_index]
        if sprite:
            stretch = 1.0 + math.sin(anim_time * 9.5) * 0.05
            target_box = (82 + int(4 * stretch), 74 + int(10 * stretch))
            target_size = fit_size(sprite.get_size(), target_box)
            scaled = pygame.transform.smoothscale(sprite, target_size)
            draw_x = rect.centerx - scaled.get_width() // 2
            draw_y = rect.bottom - scaled.get_height() + 2 + int(math.sin(anim_time * 6.2) * 2)
            surface.blit(scaled, (draw_x, draw_y))
            return
        draw_gnome(surface, rect)


class ForestLevel:
    length = 4600

    def __init__(self):
        self.target_pages = 6
        self.spawn_scale = 1.0
        self.reset()

    def reset(self):
        self.player = Player()
        self.player.reset_position(160, FOREST_GROUND_Y - 78)
        self.pages = []
        self.hazards = []
        self.particles = []
        self.camera_x = 0
        self.world_speed = 0
        self.spawn_timer = 0.0
        self.page_timer = 0.0
        self.progress = 0.0
        self.collected = 0
        self.done = False
        self.message = "Level 1: Run around the Shack, dodge anomalies, collect diary pages."

    def spawn_hazard(self):
        choice = random.choice(["gnome", "rift"])
        x = self.camera_x + WIDTH + random.randint(80, 280)
        recent_hazards = [hazard for hazard in self.hazards if hazard["rect"].x > self.camera_x + WIDTH - 220]
        if recent_hazards:
            furthest_x = max(hazard["rect"].x for hazard in recent_hazards)
            min_gap = 150 if choice == "gnome" else 280
            if choice == "rift":
                min_gap = max(
                    min_gap,
                    340 if any(hazard["type"] == "rift" for hazard in recent_hazards) else min_gap,
                )
            x = max(x, furthest_x + min_gap)
        if choice == "gnome":
            rect = pygame.Rect(x, FOREST_GROUND_Y - 52, 44, 42)
            self.hazards.append(
                {
                    "type": "gnome",
                    "rect": rect,
                    "speed": random.randint(280, 360),
                    "anim_time": random.random(),
                    "bob_phase": random.uniform(0.0, math.tau),
                }
            )
        else:
            rect = pygame.Rect(x, FOREST_GROUND_Y - 88, 34, 64)
            self.hazards.append(
                {
                    "type": "rift",
                    "rect": rect,
                    "speed": random.randint(320, 420),
                    "anim_time": random.random(),
                    "bob_phase": random.uniform(0.0, math.tau),
                }
            )

    def spawn_page(self):
        x = self.camera_x + WIDTH + random.randint(160, 420)
        y = random.randint(FOREST_GROUND_Y - 200, FOREST_GROUND_Y - 80)
        hidden = random.random() < 0.4
        self.pages.append({"rect": pygame.Rect(x, y, 28, 34), "hidden": hidden})

    def update(self, dt, keys):
        player = self.player
        player.update_common(dt)
        moving = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        retreat = keys[pygame.K_a] or keys[pygame.K_LEFT]
        player.set_motion_state(moving or retreat, dt)
        player.reveal_active = is_flashlight_pressed(keys) and player.reveal_energy > 0.2
        screen_x = player.rect.x - self.camera_x

        if moving:
            self.world_speed = 320
            player.facing = 1
            if screen_x < 330:
                player.rect.x += int(380 * dt)
            else:
                self.progress += 390 * dt
        elif retreat:
            self.world_speed = 120
            player.facing = -1
            if screen_x > 140:
                player.rect.x -= int(350 * dt)
            else:
                self.progress = max(0.0, self.progress - 180 * dt)
        else:
            self.world_speed = 0

        player.rect.x = clamp(player.rect.x, 40, self.length + 220)
        self.camera_x = clamp(self.progress, 0, self.length)

        if player.on_ground and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]):
            player.vel.y = player.jump_strength
            player.on_ground = False
            play_sfx("jump")

        player.vel.y += 1550 * dt
        player.rect.y += int(player.vel.y * dt)
        if player.rect.bottom >= FOREST_GROUND_Y:
            player.rect.bottom = FOREST_GROUND_Y
            player.vel.y = 0
            player.on_ground = True

        self.spawn_timer -= dt
        self.page_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_hazard()
            self.spawn_timer = random.uniform(0.9, 1.35) * self.spawn_scale
        if self.page_timer <= 0 and len(self.pages) < 3:
            self.spawn_page()
            self.page_timer = random.uniform(0.7, 1.15)

        # Enemy / hazard movement and damage checks for level 1.
        for hazard in list(self.hazards):
            if hazard["type"] == "gnome":
                hazard["rect"].x -= int((hazard["speed"] + self.world_speed) * dt)
            hazard["anim_time"] = hazard.get("anim_time", 0.0) + dt
            if hazard["type"] == "gnome":
                phase = hazard.get("bob_phase", 0.0)
                bob = math.sin(hazard["anim_time"] * 12 + phase) * 5
                hazard["rect"].y = FOREST_GROUND_Y - 52 + int(bob)
            else:
                phase = hazard.get("bob_phase", 0.0)
                hazard["rect"].y = FOREST_GROUND_Y - 88 + int(math.sin(hazard["anim_time"] * 4.8 + phase) * 4)
            if hazard["rect"].right < self.camera_x - 120:
                self.hazards.remove(hazard)
                continue
            if player.rect.colliderect(hazard["rect"]) and player.apply_damage():
                play_sfx("hit")
                self.particles.append(FloatText("-1", player.rect.x, player.rect.y - 18, CRIMSON))

        for page in list(self.pages):
            page["rect"].x -= int(self.world_speed * dt)
            if page["rect"].right < self.camera_x - 100:
                self.pages.remove(page)
                continue
            visible = (not page["hidden"]) or player.reveal_active
            if visible and player.rect.colliderect(page["rect"]):
                self.pages.remove(page)
                self.collected += 1
                play_sfx("page")
                message = "Hidden page" if page["hidden"] else "Page found"
                self.particles.append(FloatText(message, player.rect.x - 10, player.rect.y - 20, AMBER))

        self.particles = [p for p in self.particles if p.update(dt)]
        # Level 1 completion condition: collect all required pages.
        if self.collected >= self.target_pages:
            self.done = True
        return "lose" if player.health <= 0 else ("next" if self.done else None)

    def draw(self, surface, fonts, backgrounds=None):
        forest_layers = backgrounds.get("forest_layers") if backgrounds else None
        forest_bg = backgrounds.get("forest") if backgrounds else None
        if not draw_parallax_layers(surface, forest_layers, self.camera_x, self.length, FOREST_LAYER_OVERRIDES):
            if not draw_level_background(surface, forest_bg, self.camera_x, self.length):
                draw_forest_background(surface, self.camera_x)
        for page in self.pages:
            if page["hidden"] and not self.player.reveal_active:
                continue
            draw_page(surface, page["rect"].x - self.camera_x, page["rect"].y, pulse=True)
        for hazard in self.hazards:
            rect = hazard["rect"].move(-self.camera_x, 0)
            if hazard["type"] == "gnome":
                GnomeSprite.draw(surface, rect, hazard.get("anim_time", 0.0))
            else:
                draw_rift(surface, rect, hazard.get("anim_time", 0.0))
        self.player.draw(surface, self.camera_x)
        draw_hud(surface, fonts, self.player, self.collected, self.target_pages, 1, self.message)
        for particle in self.particles:
            alpha = int(255 * clamp(particle.life / 1.4, 0, 1))
            text = fonts["small"].render(particle.text, True, particle.color)
            text.set_alpha(alpha)
            surface.blit(text, (particle.x - self.camera_x, particle.y))


class BunkerLevel:
    def __init__(self):
        self.length = 5600
        self.reset()

    def get_completed_cipher_ids(self):
        return {cipher["id"] for cipher in self.ciphers if cipher["solved"]}

    def solve_cipher(self, cipher_id):
        cipher = next((item for item in self.ciphers if item["id"] == cipher_id), None)
        if not cipher or cipher["solved"]:
            return
        cipher["solved"] = True
        play_sfx("cipher_solve")
        reward_text = cipher.get("reward", "")
        self.particles.append(FloatText(f"{cipher['title']} solved", cipher["rect"].x - 18, cipher["rect"].y - 22, CYAN))
        if reward_text:
            self.particles.append(FloatText(reward_text, cipher["rect"].x - 60, cipher["rect"].y - 46, AMBER))

    def reset_cipher_puzzle(self, puzzle_id, message=None):
        puzzle = self.cipher_puzzles[puzzle_id]
        if puzzle["type"] in ("sequence", "plates"):
            puzzle["progress"] = 0
            for node in puzzle["nodes"]:
                node["active"] = False
        elif puzzle["type"] == "timed_seals":
            puzzle["timer"] = 0.0
            for node in puzzle["nodes"]:
                node["active"] = False
        if message:
            anchor = next((cipher for cipher in self.ciphers if cipher["id"] == puzzle_id), None)
            if anchor:
                self.particles.append(FloatText(message, anchor["rect"].x - 20, anchor["rect"].y - 20, CRIMSON))

    def reset(self):
        def stretch_x(value):
            return round(value * self.length / 4300)

        def stretch_rect(rect):
            return pygame.Rect(stretch_x(rect.x), rect.y, rect.width, rect.height)

        self.player = Player()
        self.player.reset_position(80, 420)
        self.player.health = 5
        self.camera_x = 0
        self.ceiling_y = 42
        self.gravity = 1650
        self.current_gravity = 1
        self.collected = 0
        self.target_pages = 8
        self.done = False
        self.message = "Level 2: Search the bunker, dodge creatures and traps, and decode hidden routes."
        self.particles = []
        self.interact_cooldown = 0.0
        self.platforms = [
            stretch_rect(pygame.Rect(0, 520, 360, 200)),
            stretch_rect(pygame.Rect(420, 492, 170, 24)),
            stretch_rect(pygame.Rect(650, 446, 150, 24)),
            stretch_rect(pygame.Rect(860, 398, 170, 24)),
            stretch_rect(pygame.Rect(1085, 348, 180, 24)),
            stretch_rect(pygame.Rect(1320, 392, 150, 24)),
            stretch_rect(pygame.Rect(1510, 334, 170, 24)),
            stretch_rect(pygame.Rect(1715, 272, 150, 24)),
            stretch_rect(pygame.Rect(1905, 234, 165, 24)),
            stretch_rect(pygame.Rect(2110, 282, 180, 24)),
            stretch_rect(pygame.Rect(2330, 338, 170, 24)),
            stretch_rect(pygame.Rect(2550, 396, 170, 24)),
            stretch_rect(pygame.Rect(2760, 458, 150, 24)),
            stretch_rect(pygame.Rect(2985, 404, 170, 24)),
            stretch_rect(pygame.Rect(3205, 352, 180, 24)),
            stretch_rect(pygame.Rect(3430, 298, 165, 24)),
            stretch_rect(pygame.Rect(3645, 248, 150, 24)),
            stretch_rect(pygame.Rect(3850, 302, 170, 24)),
            stretch_rect(pygame.Rect(4060, 362, 180, 24)),
            stretch_rect(pygame.Rect(4265, 420, 160, 24)),
            stretch_rect(pygame.Rect(4120, 520, 180, 200)),
        ]
        self.hidden_platforms = [
            stretch_rect(pygame.Rect(960, 318, 110, 20)),
            stretch_rect(pygame.Rect(1620, 244, 120, 20)),
            stretch_rect(pygame.Rect(2210, 214, 120, 20)),
            stretch_rect(pygame.Rect(2870, 332, 120, 20)),
            stretch_rect(pygame.Rect(3510, 232, 120, 20)),
            stretch_rect(pygame.Rect(3940, 196, 120, 20)),
        ]
        self.gravity_zones = [
            stretch_rect(pygame.Rect(1450, 94, 250, 170)),
            stretch_rect(pygame.Rect(2780, 92, 240, 170)),
            stretch_rect(pygame.Rect(3610, 86, 230, 170)),
        ]
        self.moving_platforms = [
            {
                "rect": stretch_rect(pygame.Rect(1475, 258, 130, 22)),
                "start": pygame.Vector2(stretch_x(1475), 258),
                "end": pygame.Vector2(stretch_x(1660), 198),
                "time": 0.0,
            },
            {
                "rect": stretch_rect(pygame.Rect(2460, 364, 130, 22)),
                "start": pygame.Vector2(stretch_x(2460), 364),
                "end": pygame.Vector2(stretch_x(2660), 290),
                "time": 0.8,
            },
            {
                "rect": stretch_rect(pygame.Rect(3690, 216, 140, 22)),
                "start": pygame.Vector2(stretch_x(3690), 216),
                "end": pygame.Vector2(stretch_x(3920), 216),
                "time": 1.9,
            },
        ]
        early_spike_platform = self.platforms[1]
        high_spike_platform = self.platforms[8]
        late_spike_platform = self.platforms[13]
        self.spikes = [
            pygame.Rect(early_spike_platform.centerx - 35, early_spike_platform.top - 16, 70, 16),
            pygame.Rect(high_spike_platform.centerx - 36, high_spike_platform.top - 16, 72, 16),
            pygame.Rect(late_spike_platform.centerx - 39, late_spike_platform.top - 16, 78, 16),
        ]
        self.energy_gates = [
            {"rect": stretch_rect(pygame.Rect(1190, 244, 18, 104)), "time": 0.0, "cycle": 2.2, "active_window": 1.0, "phase": 0.0},
            {"rect": stretch_rect(pygame.Rect(3340, 202, 18, 150)), "time": 0.2, "cycle": 2.4, "active_window": 0.75, "phase": 1.1},
        ]
        self.creatures = [
            {"type": "crawler", "rect": pygame.Rect(self.platforms[3].centerx - 22, self.platforms[3].top - 28, 44, 28), "left": self.platforms[3].left + 10, "right": self.platforms[3].right - 10, "speed": 86, "dir": 1, "anim": random.random(), "burn": 0.0},
            {"type": "crawler", "rect": pygame.Rect(self.platforms[9].centerx - 22, self.platforms[9].top - 28, 44, 28), "left": self.platforms[9].left + 10, "right": self.platforms[9].right - 10, "speed": 94, "dir": -1, "anim": random.random(), "burn": 0.0},
            {"type": "crawler", "rect": pygame.Rect(self.platforms[14].centerx - 22, self.platforms[14].top - 28, 44, 28), "left": self.platforms[14].left + 10, "right": self.platforms[14].right - 10, "speed": 102, "dir": -1, "anim": random.random(), "burn": 0.0},
            {"type": "wisp", "origin": pygame.Vector2(stretch_x(690), 388), "range": 66, "axis": "y", "speed": 1.8, "phase": 0.3, "radius": 18, "anim": random.random()},
            {"type": "wisp", "origin": pygame.Vector2(stretch_x(3470), 248), "range": 88, "axis": "x", "speed": 1.7, "phase": 1.2, "radius": 18, "anim": random.random()},
        ]
        glow_platform = self.platforms[4]
        stairs_platform = self.platforms[9]
        rift_platform = self.platforms[15]
        self.ciphers = [
            {
                "id": "glow",
                "title": "Lens Cipher",
                "rect": pygame.Rect(glow_platform.centerx - 27, glow_platform.top - 52, 54, 52),
                "solved": False,
                "hint": "Reveal the 3 lamps in left-to-right order.",
                "reward": "Reward: stronger diary lens in the boss fight.",
            },
            {
                "id": "stairs",
                "title": "Stair Cipher",
                "rect": pygame.Rect(stairs_platform.centerx - 27, stairs_platform.top - 52, 54, 52),
                "solved": False,
                "hint": "Step on the plates from low to high.",
                "reward": "Reward: the portal charges faster in the finale.",
            },
            {
                "id": "rift",
                "title": "Seal Cipher",
                "rect": pygame.Rect(rift_platform.centerx - 27, rift_platform.top - 52, 54, 52),
                "solved": False,
                "hint": "Reveal and seal 3 tears before the timer resets.",
                "reward": "Reward: Bill begins the last battle weakened.",
            },
        ]
        self.cipher_puzzles = {
            "glow": {
                "type": "sequence",
                "progress": 0,
                "nodes": [
                    {"rect": stretch_rect(pygame.Rect(910, 360, 34, 34)), "active": False},
                    {"rect": stretch_rect(pygame.Rect(984, 324, 34, 34)), "active": False},
                    {"rect": stretch_rect(pygame.Rect(1054, 286, 34, 34)), "active": False},
                ],
            },
            "stairs": {
                "type": "plates",
                "progress": 0,
                "order": [0, 1, 2],
                "nodes": [
                    {"rect": stretch_rect(pygame.Rect(1854, 306, 68, 16)), "active": False},
                    {"rect": stretch_rect(pygame.Rect(2010, 264, 68, 16)), "active": False},
                    {"rect": stretch_rect(pygame.Rect(2180, 206, 68, 16)), "active": False},
                ],
            },
            "rift": {
                "type": "timed_seals",
                "timer": 0.0,
                "duration": 6.8,
                "nodes": [
                    {"rect": stretch_rect(pygame.Rect(3306, 282, 34, 34)), "active": False},
                    {"rect": stretch_rect(pygame.Rect(3474, 236, 34, 34)), "active": False},
                    {"rect": stretch_rect(pygame.Rect(3726, 168, 34, 34)), "active": False},
                ],
            },
        }
        page_platform_a = self.platforms[2]
        page_platform_b = self.platforms[4]
        page_hidden_a = self.hidden_platforms[1]
        page_platform_c = self.platforms[9]
        page_hidden_b = self.hidden_platforms[3]
        page_platform_d = self.platforms[12]
        page_platform_e = self.platforms[14]
        page_platform_f = self.platforms[15]
        page_hidden_c = self.hidden_platforms[5]
        self.pages = [
            {"rect": pygame.Rect(page_platform_a.centerx - 13, page_platform_a.top - 32, 26, 32), "hidden": False, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_platform_b.centerx - 13, page_platform_b.top - 32, 26, 32), "hidden": False, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_hidden_a.centerx - 13, page_hidden_a.top - 32, 26, 32), "hidden": True, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_platform_c.centerx - 13, page_platform_c.top - 32, 26, 32), "hidden": False, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_hidden_b.centerx - 13, page_hidden_b.top - 32, 26, 32), "hidden": True, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_platform_d.centerx - 13, page_platform_d.top - 32, 26, 32), "hidden": False, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_platform_e.centerx - 13, page_platform_e.top - 32, 26, 32), "hidden": False, "taken": False, "lock": None},
            {"rect": pygame.Rect(page_platform_f.centerx - 13, page_platform_f.top - 32, 26, 32), "hidden": False, "taken": False, "lock": "rift"},
            {"rect": pygame.Rect(page_hidden_c.centerx - 13, page_hidden_c.top - 32, 26, 32), "hidden": True, "taken": False, "lock": None},
        ]
        for creature in self.creatures:
            if creature["type"] == "wisp":
                radius = creature["radius"]
                creature["rect"] = pygame.Rect(
                    round(creature["origin"].x - radius),
                    round(creature["origin"].y - radius),
                    radius * 2,
                    radius * 2,
                )

    def active_platforms(self):
        return list(self.platforms) + [item["rect"] for item in self.moving_platforms]

    def update(self, dt, keys):
        player = self.player
        player.update_common(dt)
        player.reveal_active = is_flashlight_pressed(keys) and player.reveal_energy > 0.25
        self.interact_cooldown = max(0.0, self.interact_cooldown - dt)
        interacting = keys[pygame.K_e] and self.interact_cooldown <= 0.0

        # Player movement for level 2, including zero-gravity zones and platform collisions.
        in_zero_gravity_zone = any(zone.colliderect(player.rect) for zone in self.gravity_zones)
        self.current_gravity = 0 if in_zero_gravity_zone else 1

        speed = 460
        move_x = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_x -= speed
            player.facing = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_x += speed
            player.facing = 1
        player.set_motion_state(abs(move_x) > 0, dt)

        grounded = player.on_ground
        jumped = grounded and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP])
        if jumped:
            player.vel.y = player.jump_strength
            player.on_ground = False
            play_sfx("jump")

        supporting_platform = None
        if grounded and not jumped:
            for platform in self.moving_platforms:
                base_rect = platform["rect"]
                overlap_x = player.rect.right > base_rect.left + 8 and player.rect.left < base_rect.right - 8
                standing_on_platform = abs(player.rect.bottom - base_rect.top) <= 12
                if overlap_x and standing_on_platform:
                    supporting_platform = platform
                    break

        for platform in self.moving_platforms:
            old_rect = platform["rect"].copy()
            platform["time"] += dt
            blend = (math.sin(platform["time"] * 1.4) + 1) / 2
            pos = platform["start"].lerp(platform["end"], blend)
            platform["rect"].topleft = (round(pos.x), round(pos.y))
            platform["prev_rect"] = old_rect
            platform["delta"] = pygame.Vector2(platform["rect"].x - old_rect.x, platform["rect"].y - old_rect.y)

        if supporting_platform:
            delta = supporting_platform.get("delta", pygame.Vector2())
            player.rect.x += round(delta.x)
            player.rect.y += round(delta.y)

        for platform in self.moving_platforms:
            current_rect = platform["rect"]
            prev_rect = platform.get("prev_rect", current_rect)
            dy = round(platform.get("delta", pygame.Vector2()).y)
            if not player.rect.colliderect(current_rect):
                continue
            if dy < 0 and prev_rect.top >= player.rect.bottom:
                player.rect.bottom = current_rect.top
                player.vel.y = min(player.vel.y, 0)

        previous = player.rect.copy()
        player.rect.x += int(move_x * dt)
        collision_platforms = self.active_platforms()
        if player.reveal_active:
            collision_platforms += self.hidden_platforms
        player.rect.x = clamp(player.rect.x, 20, self.length - player.rect.width - 20)

        if self.current_gravity == 0:
            player.vel.y *= 0.985
        else:
            player.vel.y += self.gravity * self.current_gravity * dt
        player.rect.y += int(player.vel.y * dt)
        player.on_ground = False
        for platform in collision_platforms:
            if player.rect.colliderect(platform):
                if can_land_on_one_way_platform(previous, player.rect, platform, player.vel.y):
                    player.rect.bottom = platform.top
                    player.vel.y = 0
                    player.on_ground = True

        if player.rect.top <= self.ceiling_y:
            player.rect.top = self.ceiling_y
            if player.vel.y < 0:
                player.vel.y = 0

        if player.rect.top > HEIGHT + 180 or player.rect.bottom < -180:
            player.health = 0

        # Enemy / hazard interactions for level 2: spikes and puzzle gates.
        for spike in self.spikes:
            if player.rect.colliderect(spike) and player.apply_damage():
                play_sfx("hit")
                self.particles.append(FloatText("-1", player.rect.x, player.rect.y - 20, CRIMSON))
                player.vel.y = -300

        for gate in self.energy_gates:
            gate["time"] += dt
            active = ((gate["time"] + gate["phase"]) % gate["cycle"]) < gate["active_window"]
            if active and player.rect.colliderect(gate["rect"]) and player.apply_damage():
                play_sfx("hit")
                self.particles.append(FloatText("Burn", player.rect.x, player.rect.y - 20, CRIMSON))
                push = -340 if player.rect.centerx < gate["rect"].centerx else 340
                player.rect.x += -20 if push < 0 else 20
                player.vel.x = push

        for creature in self.creatures:
            creature["anim"] += dt
            if creature["type"] == "crawler":
                creature["rect"].x += int(creature["speed"] * creature["dir"] * dt)
                if creature["rect"].left <= creature["left"]:
                    creature["rect"].left = creature["left"]
                    creature["dir"] = 1
                elif creature["rect"].right >= creature["right"]:
                    creature["rect"].right = creature["right"]
                    creature["dir"] = -1
                hit_rect = creature["rect"]
            else:
                axis_offset = math.sin(creature["anim"] * creature["speed"] + creature["phase"]) * creature["range"]
                center = creature["origin"].copy()
                if creature["axis"] == "x":
                    center.x += axis_offset
                else:
                    center.y += axis_offset
                radius = creature["radius"]
                hit_rect = pygame.Rect(round(center.x - radius), round(center.y - radius), radius * 2, radius * 2)
                creature["rect"] = hit_rect
            if creature["type"] == "crawler":
                in_front = (
                    (player.facing > 0 and hit_rect.centerx >= player.rect.centerx - 6)
                    or (player.facing < 0 and hit_rect.centerx <= player.rect.centerx + 6)
                )
                close_enough = abs(hit_rect.centery - player.rect.centery) < 110 and abs(hit_rect.centerx - player.rect.centerx) < 250
                if player.reveal_active and in_front and close_enough:
                    creature["burn"] = min(1.35, creature.get("burn", 0.0) + dt)
                    if creature["burn"] >= 1.35:
                        play_sfx("burn")
                        self.particles.append(FloatText("Crawler burned away", hit_rect.x - 16, hit_rect.y - 24, AMBER))
                        creature["dead"] = True
                        continue
                else:
                    creature["burn"] = max(0.0, creature.get("burn", 0.0) - dt * 0.8)
            if player.rect.colliderect(hit_rect) and player.apply_damage():
                play_sfx("hit")
                self.particles.append(FloatText("-1", player.rect.x, player.rect.y - 20, CRIMSON))
                player.vel.y = -320
        self.creatures = [creature for creature in self.creatures if not creature.get("dead")]

        for cipher in self.ciphers:
            if not cipher["solved"] and interacting and player.rect.colliderect(cipher["rect"].inflate(24, 24)):
                self.interact_cooldown = 0.25
                return ("cipher", cipher["id"])

        for page in self.pages:
            if page["taken"]:
                continue
            visible = (not page["hidden"]) or player.reveal_active
            required_cipher = page.get("lock")
            locked = required_cipher and not any(cipher["id"] == required_cipher and cipher["solved"] for cipher in self.ciphers)
            pickup_zone = player.rect.inflate(26, 28)
            if visible and not locked and pickup_zone.colliderect(page["rect"]):
                page["taken"] = True
                self.collected += 1
                play_sfx("page")
                self.particles.append(FloatText("Decoded page", page["rect"].x, page["rect"].y - 24, AMBER))

        self.camera_x = clamp(player.rect.centerx - WIDTH // 2, 0, self.length - WIDTH)
        self.particles = [p for p in self.particles if p.update(dt)]
        # Level 2 completion condition: collect every page and reach the exit side.
        if self.collected >= self.target_pages and player.rect.centerx > self.length - 220:
            self.done = True
        return "lose" if player.health <= 0 else ("next" if self.done else None)

    def draw(self, surface, fonts, backgrounds=None):
        bunker_layers = backgrounds.get("bunker_layers") if backgrounds else None
        bunker_bg = backgrounds.get("bunker") if backgrounds else None
        back_bunker_layers = bunker_layers
        front_bunker_layer = None
        if bunker_layers and len(bunker_layers) >= 5:
            back_bunker_layers = [layer for index, layer in enumerate(bunker_layers, start=1) if index != 5]
            front_bunker_layer = bunker_layers[4]
        if not draw_parallax_layers(surface, back_bunker_layers, self.camera_x, self.length - WIDTH, BUNKER_LAYER_OVERRIDES):
            if not draw_level_background(surface, bunker_bg, self.camera_x, self.length - WIDTH):
                draw_bunker_background(surface, self.camera_x, self.current_gravity == 0)
        for zone in self.gravity_zones:
            rect = zone.move(-self.camera_x, 0)
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (110, 77, 215, 45), glow.get_rect(), border_radius=20)
            surface.blit(glow, rect.topleft)
        bunker_tileset = backgrounds.get("bunker_tileset") if backgrounds else None
        bunker_palette = {
            "top": (104, 118, 132),
            "mid": (76, 86, 102),
            "shadow": (47, 53, 68),
            "crack": (58, 69, 86),
            "highlight": (166, 180, 192),
            "accent": (95, 107, 123),
        }
        ceiling_rect = pygame.Rect(0, self.ceiling_y - 34, WIDTH, 34)
        if bunker_tileset:
            draw_tiled_surface(surface, ceiling_rect, bunker_tileset, border_radius=0, overlay_color=(225, 225, 225, 255), border_color=(122, 132, 148))
        else:
            draw_stone_surface(surface, ceiling_rect, bunker_palette, self.camera_x, border_radius=0)
        for x in range(-30, WIDTH + 80, 92):
            px = x - (int(self.camera_x * 0.18) % 92)
            support = [(px, self.ceiling_y), (px + 18, self.ceiling_y), (px + 9, self.ceiling_y + 18)]
            pygame.draw.polygon(surface, (66, 74, 90), support)
        for platform in self.platforms:
            rect = platform.move(-self.camera_x, 0)
            if bunker_tileset:
                draw_tiled_surface(surface, rect, bunker_tileset, border_radius=5, overlay_color=(225, 225, 225, 255), border_color=(122, 132, 148))
            else:
                draw_stone_surface(surface, rect, bunker_palette, self.camera_x, border_radius=5)
        for platform in self.moving_platforms:
            rect = platform["rect"].move(-self.camera_x, 0)
            if bunker_tileset:
                draw_tiled_surface(surface, rect, bunker_tileset, border_radius=5, overlay_color=(225, 225, 225, 255), border_color=(122, 132, 148))
            else:
                draw_stone_surface(surface, rect, bunker_palette, self.camera_x + 60, border_radius=5)
        for hidden in self.hidden_platforms:
            rect = hidden.move(-self.camera_x, 0)
            if self.player.reveal_active:
                if bunker_tileset:
                    draw_tiled_surface(surface, rect, bunker_tileset, border_radius=4, overlay_color=(238, 242, 246, 255), border_color=(208, 224, 232))
                else:
                    draw_stone_surface(
                        surface,
                        rect,
                        {
                            "top": (214, 226, 232),
                            "mid": (185, 202, 210),
                            "shadow": (137, 155, 170),
                            "crack": (128, 148, 162),
                            "highlight": (242, 247, 250),
                            "accent": (178, 214, 220),
                        },
                        self.camera_x,
                        border_radius=4,
                    )
            else:
                pygame.draw.rect(surface, (90, 150, 150), rect, 1, border_radius=4)
        for spike in self.spikes:
            draw_spikes(surface, spike.move(-self.camera_x, 0))
        for gate in self.energy_gates:
            rect = gate["rect"].move(-self.camera_x, 0)
            active = ((gate["time"] + gate["phase"]) % gate["cycle"]) < gate["active_window"]
            draw_energy_gate(surface, rect, gate["time"], active)
        for creature in self.creatures:
            if creature["type"] == "crawler":
                draw_bunker_crawler(surface, creature["rect"].move(-self.camera_x, 0), creature["anim"], creature["dir"], creature.get("burn", 0.0))
            else:
                rect = creature["rect"].move(-self.camera_x, 0)
                draw_bunker_wisp(surface, rect, creature["anim"])
        for cipher in self.ciphers:
            rect = cipher["rect"].move(-self.camera_x, 0)
            draw_cipher_marker(surface, rect, cipher["solved"])
            title = fonts["tiny"].render(cipher["title"], True, WHITE if cipher["solved"] else MIST)
            surface.blit(title, (rect.x - 10, rect.y - 24))
            if not cipher["solved"]:
                hint = fonts["tiny"].render(cipher["hint"], True, MIST)
                surface.blit(hint, (rect.x - 110, rect.y - 52))
        for page in self.pages:
            if page["taken"]:
                continue
            if page["hidden"] and not self.player.reveal_active:
                continue
            draw_page(surface, page["rect"].x - self.camera_x, page["rect"].y)
            if page.get("lock"):
                label = fonts["tiny"].render("Solve the cipher to collect this page", True, AMBER)
                page_x = page["rect"].x - self.camera_x + 14 - label.get_width() // 2
                surface.blit(label, (page_x, page["rect"].y - 22))
        self.player.draw(surface, self.camera_x)
        draw_hud(surface, fonts, self.player, self.collected, self.target_pages, 2, self.message)
        body_font = fonts.get("body", fonts["tiny"])
        micro_font = fonts.get("micro", fonts["tiny"])
        gravity_rect = pygame.Rect(WIDTH - 238, 116, 210, 34)
        gravity_label = "Zero gravity" if self.current_gravity == 0 else "Normal gravity"
        draw_note_chip(surface, gravity_rect, gravity_label, body_font, text_color=(58, 32, 18))
        solved_count = len(self.get_completed_cipher_ids())
        status_rect = pygame.Rect(22, 116, 260, 34)
        draw_note_chip(surface, status_rect, f"Ciphers {solved_count}/3  |  E: interact", micro_font, text_color=(78, 46, 20), pin=True)
        for particle in self.particles:
            alpha = int(255 * clamp(particle.life / 1.4, 0, 1))
            text = fonts["small"].render(particle.text, True, particle.color)
            text.set_alpha(alpha)
            surface.blit(text, (particle.x - self.camera_x, particle.y))
        if front_bunker_layer:
            draw_parallax_layers(
                surface,
                [front_bunker_layer],
                self.camera_x,
                self.length - WIDTH,
                {1: BUNKER_LAYER_OVERRIDES.get(5, {})},
            )


class BossLevel:
    sprites = []

    @classmethod
    def set_sprite(cls, sprite):
        cls.sprites = []
        if sprite is None:
            return
        width, height = sprite.get_size()
        frames = []
        if width > height and width % height == 0:
            frame_count = width // height
            for index in range(frame_count):
                frame = sprite.subsurface((index * height, 0, height, height)).copy()
                frames.append(trim_transparent_bounds(frame))
        else:
            frames.append(trim_transparent_bounds(sprite))
        cls.sprites = [frame for frame in frames if frame is not None]

    def __init__(self):
        self.length = 3000
        self.reset()

    def reset(self):
        self.player = Player()
        self.player.reset_position(90, GROUND_Y - 78)
        self.player.health = 6
        self.player.max_health = 6
        self.message = "Level 3: Survive Bill's shadow, reveal weak points, then charge the portal with Stan."
        self.camera_x = 0
        self.particles = []
        self.platforms = [
            pygame.Rect(210, 520, 220, 24),
            pygame.Rect(500, 456, 170, 24),
            pygame.Rect(760, 396, 160, 24),
            pygame.Rect(1040, 344, 170, 24),
            pygame.Rect(1320, 294, 150, 24),
            pygame.Rect(1600, 294, 150, 24),
            pygame.Rect(1875, 344, 170, 24),
            pygame.Rect(2145, 396, 160, 24),
            pygame.Rect(2405, 456, 170, 24),
            pygame.Rect(2650, 520, 180, 24),
        ]
        self.hidden_platforms = [
            pygame.Rect(640, 326, 130, 20),
            pygame.Rect(1470, 154, 130, 20),
            pygame.Rect(2240, 326, 130, 20),
        ]
        self.boss_rect = pygame.Rect(self.length // 2 - 80, 145, 160, 190)
        self.boss_anchor_x = [880, self.length // 2, 2120]
        self.boss_teleport_timer = 1.9
        self.boss_max_health = 6
        self.boss_health = self.boss_max_health
        self.boss_fire_timer = 1.1
        self.ground_burst_timer = 6.4
        self.distortion = 0.0
        self.projectiles = []
        self.telegraphs = []
        self.ground_telegraphs = []
        self.weak_points = []
        self.weak_timer = 2.8
        self.stan_ready = False
        self.stan_rect = pygame.Rect(self.length - 250, GROUND_Y - 82, 46, 82)
        self.portal_rect = pygame.Rect(self.length - 190, 420, 88, 180)
        self.portal_charge_goal = 3.2
        self.weak_point_life_bonus = 0.0
        self.true_escape = False
        self.win = False
        self.phase_two_started = False
        self.phase_two_transition = False
        self.phase_two_timer = 0.0
        self.phase_two_threshold = max(3, math.ceil(self.boss_max_health / 2))
        self.anchor_rift = None
        self.anchor_rift_cooldown = 2.2
        self.boss_defeat_started = False
        self.boss_defeat_timer = 0.0
        self.boss_rift_center = pygame.Vector2(self.boss_rect.centerx + 10, self.boss_rect.centery - 8)
        self.boss_rift_base_size = pygame.Vector2(210, 276)

    def apply_bunker_bonuses(self, solved_ciphers):
        solved = set(solved_ciphers)
        self.true_escape = len(solved) >= 3
        self.player.max_reveal = max(self.player.max_reveal, 5.5)
        if "glow" in solved:
            self.player.max_reveal += 1.5
            self.player.reveal_energy = self.player.max_reveal
            self.weak_point_life_bonus = 1.2
        if "stairs" in solved:
            self.portal_charge_goal = 2.35
        if "rift" in solved:
            self.boss_max_health = 5
            self.boss_health = min(self.boss_health, self.boss_max_health)
        else:
            self.boss_max_health = 6
            self.boss_health = min(self.boss_health, self.boss_max_health)
        self.phase_two_threshold = max(3, math.ceil(self.boss_max_health / 2))

    def create_dark_energy_attack(self, origin=None, target=None, angle_jitter=18):
        origin = pygame.Vector2(origin or (self.boss_rect.centerx, self.boss_rect.centery))
        target = pygame.Vector2(target or (self.player.rect.centerx, self.player.rect.centery))
        direction = target - origin
        if direction.length() == 0:
            direction = pygame.Vector2(-1, 0)
        direction = direction.normalize()
        direction.rotate_ip(random.uniform(-angle_jitter, angle_jitter))
        return {
            "origin": pygame.Vector2(origin),
            "dir": pygame.Vector2(direction),
            "travel": 0.0,
            "speed": random.uniform(1180, 1460),
            "max_length": random.randint(540, 760),
            "width": random.randint(9, 13),
            "wave_amp": random.uniform(10.0, 18.0),
            "wave_freq": random.uniform(8.0, 12.0),
            "wave_speed": random.uniform(7.0, 10.0),
            "phase": random.uniform(0.0, math.tau),
            "anim_time": 0.0,
        }

    def spawn_projectile(self):
        self.projectiles.append(self.create_dark_energy_attack())

    def queue_telegraphed_attack(self, origin=None, target=None, timer=0.42, angle_jitter=18):
        attack = self.create_dark_energy_attack(origin=origin, target=target, angle_jitter=angle_jitter)
        attack["travel"] = attack["max_length"]
        self.telegraphs.append({"attack": attack, "timer": timer})
        play_sfx("boss_attack")

    def queue_ground_burst(self):
        burst_count = random.randint(4, 6)
        arena_left = 220
        arena_right = self.length - 220
        candidate_x = [360, 560, 820, 1060, 1300, 1540, 1780, 2020, 2260, 2500, 2740]
        player_bias = clamp(self.player.rect.centerx, arena_left, arena_right)
        candidate_x.sort(key=lambda x: (abs(x - player_bias), random.random()))
        chosen = sorted(candidate_x[:burst_count])
        for x in chosen:
            self.ground_telegraphs.append(
                {
                    "x": x,
                    "timer": 0.72,
                    "width": random.randint(26, 38),
                    "phase": random.uniform(0.0, math.tau),
                }
            )

    def spawn_weak_point(self):
        if len(self.weak_points) >= 2:
            return
        pool = [
            pygame.Rect(self.boss_rect.left - 340, 470, 34, 34),
            pygame.Rect(self.boss_rect.left - 270, 400, 34, 34),
            pygame.Rect(self.boss_rect.left - 190, 330, 34, 34),
            pygame.Rect(self.boss_rect.left - 105, 250, 34, 34),
            pygame.Rect(self.boss_rect.centerx - 110, 165, 34, 34),
            pygame.Rect(self.boss_rect.centerx - 17, 210, 34, 34),
            pygame.Rect(self.boss_rect.centerx + 74, 165, 34, 34),
            pygame.Rect(self.boss_rect.right + 70, 250, 34, 34),
            pygame.Rect(self.boss_rect.right + 150, 330, 34, 34),
            pygame.Rect(self.boss_rect.right + 230, 400, 34, 34),
            pygame.Rect(self.boss_rect.right + 300, 470, 34, 34),
        ]
        rect = random.choice(pool).copy()
        if any(item["rect"].colliderect(rect) for item in self.weak_points):
            return
        self.weak_points.append({"rect": rect, "life": 4.0 + self.weak_point_life_bonus})

    def start_phase_two_transition(self):
        if self.phase_two_started or self.phase_two_transition or self.boss_defeat_started:
            return
        self.phase_two_transition = True
        self.phase_two_timer = 0.0
        self.anchor_rift = None
        self.projectiles.clear()
        self.telegraphs.clear()
        self.ground_telegraphs.clear()
        self.weak_points.clear()
        self.boss_rect.centerx = self.length // 2
        self.boss_teleport_timer = 1.0
        self.boss_fire_timer = 0.7
        self.ground_burst_timer = 2.6
        self.weak_timer = 1.7
        self.distortion = 1.0
        self.message = "Phase 2: Bill tears open anchors in the arena."
        play_sfx("boss_teleport")
        self.particles.append(FloatText("The tear widens", self.boss_rect.x - 30, self.boss_rect.y - 34, AMBER, 1.8))

    def spawn_anchor_rift(self):
        candidate_x = [420, 720, 1030, 1360, 1650, 1960, 2270, 2570]
        viable = [x for x in candidate_x if abs(x - self.player.rect.centerx) > 180]
        x = random.choice(viable or candidate_x)
        y = random.choice([188, 236, 284, 332])
        self.anchor_rift = {
            "center": pygame.Vector2(x, y),
            "life": 4.8,
            "fire_timer": 0.45,
            "phase": random.uniform(0.0, math.tau),
            "radius": random.randint(42, 54),
        }
        self.distortion = max(self.distortion, 0.72)
        play_sfx("boss_teleport")
        self.particles.append(FloatText("Anchor rift", x - 44, y - 36, CYAN, 1.3))

    def update_phase_two(self, dt):
        if self.phase_two_transition:
            self.phase_two_timer += dt
            self.distortion = max(self.distortion, 0.35)
            if self.phase_two_timer >= 1.05:
                self.phase_two_transition = False
                self.phase_two_started = True
                self.anchor_rift_cooldown = 0.35
            return

        self.anchor_rift_cooldown = max(0.0, self.anchor_rift_cooldown - dt)
        if self.anchor_rift is None and self.anchor_rift_cooldown <= 0.0:
            self.spawn_anchor_rift()

        if not self.anchor_rift:
            return

        self.anchor_rift["life"] -= dt
        self.anchor_rift["fire_timer"] -= dt
        if self.anchor_rift["fire_timer"] <= 0:
            self.queue_telegraphed_attack(
                origin=self.anchor_rift["center"],
                target=(self.player.rect.centerx, self.player.rect.centery),
                timer=0.28,
                angle_jitter=10,
            )
            self.anchor_rift["fire_timer"] = random.uniform(0.72, 0.98)

        hit_rect = pygame.Rect(0, 0, self.anchor_rift["radius"] * 2, self.anchor_rift["radius"] * 2)
        hit_rect.center = (round(self.anchor_rift["center"].x), round(self.anchor_rift["center"].y))
        if self.player.rect.colliderect(hit_rect.inflate(10, 14)) and self.player.apply_damage():
            play_sfx("hit")
            self.particles.append(FloatText("Tear burn", self.player.rect.x - 8, self.player.rect.y - 18, CRIMSON))
            push = -260 if self.player.rect.centerx < hit_rect.centerx else 260
            self.player.rect.x += -18 if push < 0 else 18

        if self.anchor_rift["life"] <= 0:
            self.particles.append(FloatText("Anchor sealed", self.anchor_rift["center"].x - 44, self.anchor_rift["center"].y - 24, AMBER, 1.2))
            self.anchor_rift = None
            self.anchor_rift_cooldown = random.uniform(2.2, 3.4)

    def start_boss_defeat_sequence(self):
        if self.boss_defeat_started:
            return
        self.boss_defeat_started = True
        self.phase_two_transition = False
        self.boss_defeat_timer = 0.0
        self.boss_rift_center = pygame.Vector2(self.boss_rect.centerx + 10, self.boss_rect.centery - 8)
        self.anchor_rift = None
        self.projectiles.clear()
        self.telegraphs.clear()
        self.ground_telegraphs.clear()
        self.weak_points.clear()
        self.distortion = 0.95
        play_sfx("boss_teleport")
        self.particles.append(FloatText("Bill's shadow is dragged into the tear", self.boss_rect.x - 90, self.boss_rect.y - 30, CYAN, 1.9))

    def update_boss_defeat_sequence(self, dt):
        self.boss_defeat_timer += dt
        self.distortion = max(self.distortion, 0.25)
        if self.boss_defeat_timer >= 1.55:
            self.boss_defeat_started = False
            self.stan_ready = True
            self.message = "Level 3: Bill is gone. Find Stan and charge the portal."

    def draw_boss_entity(self, surface, boss_rect, hover_time, alpha=255, scale=1.0, extra_offset=(0, 0), pulse_boost=1.0):
        hover_y = math.sin(hover_time * 2.2) * 14 + math.sin(hover_time * 4.4 + 0.8) * 4
        sway_x = math.sin(hover_time * 1.6 + 0.4) * 6
        offset_x = round(sway_x + extra_offset[0])
        offset_y = round(hover_y + extra_offset[1])
        if BossLevel.sprites:
            frame_index = int(pygame.time.get_ticks() * 0.0012) % len(BossLevel.sprites)
            boss_sprite = BossLevel.sprites[frame_index]
            target_size = fit_size(
                boss_sprite.get_size(),
                (max(32, int((boss_rect.width + 90) * scale)), max(32, int((boss_rect.height + 90) * scale))),
            )
            scaled = pygame.transform.smoothscale(boss_sprite, target_size)
            pulse = (0.92 + 0.08 * math.sin(pygame.time.get_ticks() * 0.0013)) * pulse_boost
            if pulse != 1.0:
                tinted = scaled.copy()
                tinted.fill((int(20 * pulse), int(40 * pulse), int(75 * pulse), 0), special_flags=pygame.BLEND_RGBA_ADD)
                scaled = tinted
            if alpha < 255:
                scaled.set_alpha(alpha)
            shadow_rect = pygame.Rect(0, 0, max(18, int(scaled.get_width() * 0.72)), max(8, int(22 * scale)))
            shadow_rect.center = (boss_rect.centerx, boss_rect.bottom + 26)
            shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (8, 6, 14, min(105, max(0, int(alpha * 0.45)))), shadow.get_rect())
            surface.blit(shadow, shadow_rect.topleft)
            draw_rect = scaled.get_rect(center=(boss_rect.centerx + offset_x, boss_rect.centery + offset_y))
            surface.blit(scaled, draw_rect.topleft)
        else:
            scaled_size = (max(26, int(boss_rect.width * scale)), max(42, int(boss_rect.height * scale)))
            floating_rect = pygame.Rect(0, 0, *scaled_size)
            floating_rect.center = (boss_rect.centerx + offset_x, boss_rect.centery + offset_y)
            shadow_rect = pygame.Rect(0, 0, max(18, int(floating_rect.width * 0.72)), max(8, int(18 * scale)))
            shadow_rect.center = (boss_rect.centerx, boss_rect.bottom + 18)
            shadow = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (8, 6, 14, min(100, max(0, int(alpha * 0.4)))), shadow.get_rect())
            surface.blit(shadow, shadow_rect.topleft)
            fallback = pygame.Surface(floating_rect.size, pygame.SRCALPHA)
            draw_bill_shadow(fallback, fallback.get_rect(), self.boss_health)
            if alpha < 255:
                fallback.set_alpha(alpha)
            surface.blit(fallback, floating_rect.topleft)

    def draw_boss_defeat_effect(self, surface):
        boss_rect = self.boss_rect.move(-self.camera_x, 0)
        timer = self.boss_defeat_timer
        open_progress = clamp(timer / 0.34, 0.0, 1.0)
        close_progress = clamp((timer - 1.0) / 0.42, 0.0, 1.0)
        rift_strength = open_progress * (1.0 - close_progress)
        if rift_strength > 0.02:
            width = max(18, int(self.boss_rift_base_size.x * rift_strength))
            height = max(32, int(self.boss_rift_base_size.y * rift_strength))
            rift_rect = pygame.Rect(0, 0, width, height)
            rift_rect.center = (round(self.boss_rift_center.x - self.camera_x), round(self.boss_rift_center.y))
            draw_rift(surface, rift_rect, timer * 2.8)
        pull_progress = clamp((timer - 0.16) / 0.82, 0.0, 1.0)
        if pull_progress < 1.0:
            target_center = pygame.Vector2(self.boss_rift_center.x - self.camera_x, self.boss_rift_center.y)
            current_center = pygame.Vector2(boss_rect.center)
            offset = (target_center - current_center) * (pull_progress * 0.8)
            scale = 1.0 - 0.58 * pull_progress
            alpha = int(255 * (1.0 - 0.88 * pull_progress))
            self.draw_boss_entity(
                surface,
                boss_rect,
                pygame.time.get_ticks() * 0.001,
                alpha=alpha,
                scale=scale,
                extra_offset=(offset.x, offset.y),
                pulse_boost=1.15,
            )

    def draw_anchor_rift(self, surface):
        if not self.anchor_rift:
            return
        pulse = 1.0 + math.sin(pygame.time.get_ticks() * 0.01 + self.anchor_rift["phase"]) * 0.16
        radius = max(18, int(self.anchor_rift["radius"] * pulse))
        rect = pygame.Rect(0, 0, radius * 2, int(radius * 2.5))
        rect.center = (round(self.anchor_rift["center"].x - self.camera_x), round(self.anchor_rift["center"].y))
        draw_rift(surface, rect, pygame.time.get_ticks() * 0.003 + self.anchor_rift["phase"])
        ring = pygame.Surface((rect.width + 50, rect.height + 40), pygame.SRCALPHA)
        pygame.draw.ellipse(ring, (112, 224, 255, 38), ring.get_rect(), width=8)
        surface.blit(ring, (rect.x - 25, rect.y - 20))

    def update(self, dt, keys):
        player = self.player
        player.update_common(dt)
        player.reveal_active = is_flashlight_pressed(keys) and player.reveal_energy > 0.2

        # Player movement for level 3: arena traversal, jumping, and platform collisions.
        move_x = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_x -= player.speed
            player.facing = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_x += player.speed
            player.facing = 1
        player.set_motion_state(abs(move_x) > 0, dt)
        if player.on_ground and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]):
            player.vel.y = player.jump_strength
            player.on_ground = False
            play_sfx("jump")

        previous = player.rect.copy()
        player.rect.x += int(move_x * dt)
        player.rect.x = clamp(player.rect.x, 20, self.length - player.rect.width - 20)

        collision_platforms = list(self.platforms)
        if player.reveal_active:
            collision_platforms += self.hidden_platforms

        player.vel.y += 1650 * dt
        player.rect.y += int(player.vel.y * dt)
        player.on_ground = False
        for platform in collision_platforms + [pygame.Rect(0, GROUND_Y, self.length, 120)]:
            if player.rect.colliderect(platform) and can_land_on_one_way_platform(previous, player.rect, platform, player.vel.y):
                player.rect.bottom = platform.top
                player.vel.y = 0
                player.on_ground = True

        if not self.stan_ready and not self.boss_defeat_started and not self.phase_two_transition:
            self.boss_teleport_timer -= dt
            if self.boss_teleport_timer <= 0:
                choices = [anchor for anchor in self.boss_anchor_x if abs(anchor - self.boss_rect.centerx) > 20]
                if choices:
                    self.boss_rect.centerx = random.choice(choices)
                    self.distortion = max(self.distortion, 0.5)
                    play_sfx("boss_teleport")
                self.boss_teleport_timer = random.uniform(2.4, 3.8)

        self.camera_x = clamp(player.rect.centerx - WIDTH // 2, 0, self.length - WIDTH)

        self.boss_fire_timer -= dt
        if self.boss_fire_timer <= 0 and not self.stan_ready and not self.boss_defeat_started and not self.phase_two_transition:
            self.queue_telegraphed_attack()
            self.boss_fire_timer = 0.48 if self.phase_two_started else (0.86 if self.boss_health > 5 else 0.58)
        self.ground_burst_timer -= dt
        if self.ground_burst_timer <= 0 and not self.stan_ready and not self.boss_defeat_started and not self.phase_two_transition:
            self.queue_ground_burst()
            self.ground_burst_timer = random.uniform(5.2, 7.0) if self.phase_two_started else random.uniform(6.8, 9.2)
        for warning in list(self.telegraphs):
            warning["timer"] -= dt
            warning["attack"]["anim_time"] += dt
            if warning["timer"] <= 0:
                released = warning["attack"].copy()
                released["origin"] = pygame.Vector2(warning["attack"]["origin"])
                released["dir"] = pygame.Vector2(warning["attack"]["dir"])
                released["travel"] = 0.0
                released["anim_time"] = 0.0
                self.projectiles.append(released)
                self.telegraphs.remove(warning)
        for warning in list(self.ground_telegraphs):
            warning["timer"] -= dt
            if warning["timer"] <= 0:
                direction = pygame.Vector2(random.uniform(-0.22, 0.22), -1).normalize()
                self.projectiles.append(
                    {
                        "origin": pygame.Vector2(warning["x"], GROUND_Y),
                        "dir": direction,
                        "travel": 0.0,
                        "speed": random.uniform(980, 1180),
                        "max_length": random.randint(300, 420),
                        "width": random.randint(8, 12),
                        "wave_amp": random.uniform(12.0, 22.0),
                        "wave_freq": random.uniform(9.0, 14.0),
                        "wave_speed": random.uniform(8.0, 12.0),
                        "phase": warning["phase"],
                        "anim_time": 0.0,
                    }
                )
                self.ground_telegraphs.remove(warning)
        # Enemy attack logic for level 3: boss projectiles and weak-point phases.
        for projectile in list(self.projectiles):
            projectile["anim_time"] += dt
            projectile["travel"] += projectile["speed"] * dt
            if projectile["travel"] >= projectile["max_length"]:
                self.projectiles.remove(projectile)
                continue
            hit = False
            for point in build_dark_energy_points(projectile):
                if player.rect.collidepoint(point):
                    hit = True
                    break
            if hit:
                if player.apply_damage():
                    play_sfx("hit")
                    self.particles.append(FloatText("-1", player.rect.x, player.rect.y - 18, CRIMSON))
                self.projectiles.remove(projectile)

        self.weak_timer -= dt
        if self.weak_timer <= 0 and not self.stan_ready and not self.boss_defeat_started and not self.phase_two_transition:
            self.spawn_weak_point()
            self.weak_timer = random.uniform(1.6, 2.3) if self.phase_two_started else random.uniform(2.2, 3.3)
        for point in list(self.weak_points):
            point["life"] -= dt
            if point["life"] <= 0:
                self.weak_points.remove(point)
                continue
            if player.reveal_active and player.rect.colliderect(point["rect"]):
                self.weak_points.remove(point)
                self.boss_health -= 1
                self.distortion = 0.6
                play_sfx("cipher_solve")
                self.particles.append(FloatText("Weak point broken", point["rect"].x - 30, point["rect"].y - 20, CYAN))

        if 0 < self.boss_health <= self.phase_two_threshold and not self.phase_two_started and not self.phase_two_transition and not self.boss_defeat_started:
            self.start_phase_two_transition()
        if self.phase_two_started or self.phase_two_transition:
            self.update_phase_two(dt)
        self.distortion = max(0.0, self.distortion - dt)
        if self.boss_health <= 0 and not self.stan_ready:
            self.start_boss_defeat_sequence()
        if self.boss_defeat_started:
            self.update_boss_defeat_sequence(dt)
        if self.stan_ready and player.rect.colliderect(self.stan_rect):
            self.stan_ready = "met"
        close_to_portal = player.rect.colliderect(self.portal_rect.inflate(30, 30))
        if self.stan_ready and close_to_portal and keys[pygame.K_e]:
            player.portal_charge += dt
            if player.portal_charge >= self.portal_charge_goal:
                play_sfx("portal")
                self.win = True
        else:
            player.portal_charge = max(0.0, player.portal_charge - dt * 0.75)

        self.particles = [p for p in self.particles if p.update(dt)]
        # Level 3 completion condition: survive, defeat the boss phase, then charge the portal.
        if player.health <= 0:
            return "lose"
        if self.win:
            return "win"
        return None

    def draw(self, surface, fonts, backgrounds=None):
        boss_bg = backgrounds.get("boss") if backgrounds else None
        if not draw_level_background(surface, boss_bg, self.camera_x, self.length - WIDTH):
            draw_boss_background(surface, self.distortion)
        arena_floor = pygame.Rect(-self.camera_x, GROUND_Y, self.length, HEIGHT - GROUND_Y)
        draw_stone_surface(
            surface,
            arena_floor,
            {
                "top": (89, 77, 72),
                "mid": (58, 46, 52),
                "shadow": (28, 21, 29),
                "crack": (105, 77, 72),
                "highlight": (141, 117, 108),
                "accent": (82, 60, 58),
            },
            self.camera_x,
            border_radius=0,
        )
        for platform in self.platforms:
            draw_stone_surface(
                surface,
                platform.move(-self.camera_x, 0),
                {
                    "top": (95, 106, 132),
                    "mid": (66, 74, 98),
                    "shadow": (35, 40, 56),
                    "crack": (114, 126, 154),
                    "highlight": (163, 175, 201),
                    "accent": (84, 94, 120),
                },
                self.camera_x,
                border_radius=6,
            )
        for platform in self.hidden_platforms:
            rect = platform.move(-self.camera_x, 0)
            if self.player.reveal_active:
                draw_stone_surface(
                    surface,
                    rect,
                    {
                        "top": (212, 226, 232),
                        "mid": (182, 198, 208),
                        "shadow": (129, 145, 160),
                        "crack": (126, 148, 168),
                        "highlight": (242, 246, 249),
                        "accent": (168, 218, 228),
                    },
                    self.camera_x,
                    border_radius=6,
                )
            else:
                pygame.draw.rect(surface, (91, 145, 152), rect, 1, border_radius=6)
        draw_portal(surface, self.portal_rect.move(-self.camera_x, 0), self.player.portal_charge / self.portal_charge_goal)
        self.draw_anchor_rift(surface)
        if self.boss_defeat_started:
            self.draw_boss_defeat_effect(surface)
        elif not self.stan_ready:
            self.draw_boss_entity(surface, self.boss_rect.move(-self.camera_x, 0), pygame.time.get_ticks() * 0.001)
        else:
            draw_stan(surface, self.stan_rect.move(-self.camera_x, 0))
        for warning in self.telegraphs:
            draw_attack_telegraph(surface, warning["attack"], warning["timer"], self.camera_x)
        for warning in self.ground_telegraphs:
            draw_ground_attack_telegraph(surface, warning, self.camera_x)
        for projectile in self.projectiles:
            draw_dark_energy_stream(surface, projectile, self.camera_x)
        for point in self.weak_points:
            color = CYAN if self.player.reveal_active else (71, 103, 111)
            center = (point["rect"].centerx - self.camera_x, point["rect"].centery)
            pygame.draw.circle(surface, color, center, 18, 3)
            pygame.draw.circle(surface, color, center, 6)
        self.player.draw(surface, self.camera_x)
        draw_hud(surface, fonts, self.player, max(0, self.boss_max_health - self.boss_health), self.boss_max_health, 3, self.message)
        boss_text = fonts["small"].render(f"Bill's shadow: {max(0, self.boss_health)}/{self.boss_max_health}", True, WHITE)
        surface.blit(boss_text, (WIDTH - 240, 88))
        if self.boss_defeat_started:
            text = fonts["small"].render("Bill's shadow is collapsing into the tear", True, CYAN)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, 110))
        elif self.phase_two_transition:
            text = fonts["small"].render("Phase 2: the arena is splitting open", True, AMBER)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, 110))
        elif self.phase_two_started:
            text = fonts["small"].render("Phase 2: anchor rifts fire from the arena", True, CYAN)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, 110))
        elif self.stan_ready:
            text = fonts["small"].render("Hold E near portal to escape", True, AMBER)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, 110))
        bonus_parts = []
        if self.weak_point_life_bonus > 0:
            bonus_parts.append("Lens boost")
        if self.portal_charge_goal < 3.2:
            bonus_parts.append("Fast portal")
        if self.boss_max_health < 12:
            bonus_parts.append("Weakened Bill")
        if bonus_parts:
            bonus_text = fonts["tiny"].render("Cipher bonuses: " + ", ".join(bonus_parts), True, CYAN)
            surface.blit(bonus_text, (26, 118))
        for particle in self.particles[-4:]:
            alpha = int(255 * clamp(particle.life / 1.4, 0, 1))
            text = fonts["small"].render(particle.text, True, particle.color)
            text.set_alpha(alpha)
            surface.blit(text, (particle.x - self.camera_x, particle.y))


def draw_forest_background(surface, camera_x):
    surface.fill(SKY)
    pygame.draw.circle(surface, (252, 249, 226), (int(1050 - camera_x * 0.04), 110), 44)
    for layer, color, factor, height_scale in [
        (0, FOREST_LIGHT, 0.2, 180),
        (1, FOREST_MID, 0.38, 240),
        (2, FOREST_DARK, 0.56, 320),
    ]:
        offset = camera_x * factor
        for i in range(-2, 9):
            base_x = i * 190 - (offset % 190)
            top = 200 + layer * 30 + (i % 3) * 18
            pygame.draw.polygon(surface, color, [(base_x, HEIGHT), (base_x + 80, top), (base_x + 160, HEIGHT)])
            pygame.draw.rect(surface, color, (base_x + 68, HEIGHT - height_scale, 18, height_scale))
    draw_forest_ground(surface, FOREST_GROUND_Y, camera_x)


def draw_shack(surface, x, y):
    pygame.draw.rect(surface, (129, 88, 55), (x, y, 210, 180), border_radius=6)
    pygame.draw.polygon(surface, (88, 38, 24), [(x - 18, y + 20), (x + 104, y - 46), (x + 228, y + 20)])
    pygame.draw.rect(surface, (78, 54, 32), (x + 80, y + 74, 46, 106))
    pygame.draw.circle(surface, (232, 198, 107), (int(x + 56), int(y + 74)), 20, 4)
    pygame.draw.rect(surface, (170, 126, 78), (x + 22, y - 16, 168, 34), border_radius=8)


def draw_page(surface, x, y, pulse=False):
    wobble = math.sin(pygame.time.get_ticks() * 0.01 + x * 0.05) * 4 if pulse else 0
    rect = pygame.Rect(x, y + wobble, 28, 34)
    pygame.draw.rect(surface, PAPER, rect, border_radius=4)
    pygame.draw.rect(surface, (155, 121, 82), rect, 2, border_radius=4)
    for line in range(4):
        pygame.draw.line(surface, (166, 145, 104), (rect.x + 6, rect.y + 8 + line * 6), (rect.right - 6, rect.y + 8 + line * 6), 1)


def draw_gnome(surface, rect):
    body = rect.inflate(-4, -4)
    pygame.draw.ellipse(surface, (92, 120, 82), (body.x + 8, body.y + 18, body.width - 12, body.height - 18))
    pygame.draw.polygon(surface, (178, 34, 38), [(body.x + 8, body.y + 20), (body.centerx, body.y - 8), (body.right - 2, body.y + 18)])
    pygame.draw.circle(surface, (236, 205, 180), (body.x + 22, body.y + 24), 11)
    pygame.draw.circle(surface, (216, 152, 122), (body.x + 27, body.y + 27), 4)
    pygame.draw.polygon(surface, WHITE, [(body.x + 10, body.y + 30), (body.x + 34, body.y + 30), (body.x + 22, body.bottom)])
    pygame.draw.line(surface, BLACK, (body.x + 16, body.y + 18), (body.x + 22, body.y + 16), 1)
    pygame.draw.line(surface, BLACK, (body.x + 24, body.y + 17), (body.x + 30, body.y + 15), 1)
    pygame.draw.circle(surface, BLACK, (body.x + 18, body.y + 21), 2)
    pygame.draw.circle(surface, BLACK, (body.x + 26, body.y + 20), 2)


def draw_rift(surface, rect, anim_time=0.0):
    pulse = 1.0 + math.sin(anim_time * 7.0) * 0.12
    wobble = int(math.sin(anim_time * 11.0) * 2)
    glow_pad = 11 + int(5 * pulse)
    glow = pygame.Surface((rect.width + glow_pad * 2, rect.height + glow_pad * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (102, 231, 255, 42 + int(26 * pulse)), glow.get_rect())
    surface.blit(glow, (rect.x - glow_pad, rect.y - glow_pad))

    active = rect.inflate(int(rect.width * (pulse - 1) * 0.45), int(rect.height * (pulse - 1) * 0.7))
    active.y += wobble
    pygame.draw.ellipse(surface, CYAN, active, 3)
    pygame.draw.line(surface, WHITE, active.midtop, active.midbottom, 2)
    pygame.draw.line(surface, (180, 247, 255), (active.centerx - 4, active.y + 8), (active.centerx + 5, active.bottom - 10), 1)


def draw_bunker_background(surface, camera_x, inverted):
    top = (23, 28, 43) if not inverted else (36, 22, 46)
    bottom = (10, 13, 24)
    for y in range(HEIGHT):
        blend = y / HEIGHT
        color = tuple(int(top[i] * (1 - blend) + bottom[i] * blend) for i in range(3))
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))
    for x in range(-40, WIDTH + 80, 120):
        px = x - int(camera_x * 0.2) % 120
        pygame.draw.rect(surface, (39, 48, 68), (px, 0, 18, HEIGHT))
    for y in range(120, HEIGHT, 120):
        pygame.draw.line(surface, (54, 63, 88), (0, y), (WIDTH, y), 2)

    # Make the lower area read as a hazardous maintenance shaft instead of safe floor.
    shaft_top = 604
    for y in range(shaft_top, HEIGHT):
        blend = (y - shaft_top) / max(1, HEIGHT - shaft_top)
        color = (
            int(18 * (1 - blend) + 6 * blend),
            int(22 * (1 - blend) + 5 * blend),
            int(30 * (1 - blend) + 8 * blend),
        )
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))

    warning_band = pygame.Rect(0, shaft_top - 10, WIDTH, 14)
    pygame.draw.rect(surface, (92, 78, 54), warning_band)
    for x in range(-40, WIDTH + 80, 56):
        px = x - (int(camera_x * 0.15) % 56)
        stripe = [(px, shaft_top + 4), (px + 18, shaft_top + 4), (px + 4, shaft_top - 10), (px - 14, shaft_top - 10)]
        pygame.draw.polygon(surface, (196, 164, 86), stripe)

    for x in range(-30, WIDTH + 40, 84):
        px = x - (int(camera_x * 0.22) % 84)
        pipe_h = 26 + ((x // 84) % 3) * 12
        pygame.draw.rect(surface, (28, 36, 48), (px, shaft_top + 18, 20, pipe_h), border_radius=4)
        pygame.draw.rect(surface, (56, 68, 84), (px + 4, shaft_top + 18, 4, pipe_h))

    for x in range(-20, WIDTH + 60, 68):
        px = x - (int(camera_x * 0.35) % 68)
        points = [(px, HEIGHT), (px + 14, shaft_top + 38), (px + 28, HEIGHT)]
        pygame.draw.polygon(surface, (126, 54, 58), points)
        pygame.draw.polygon(surface, (214, 118, 94), points, 1)

    haze = pygame.Surface((WIDTH, HEIGHT - shaft_top), pygame.SRCALPHA)
    for index in range(5):
        ellipse = pygame.Rect(120 * index - 40, 20 + index * 18, WIDTH // 3, 54)
        pygame.draw.ellipse(haze, (120, 36, 38, 14), ellipse)
    surface.blit(haze, (0, shaft_top))


def draw_spikes(surface, rect):
    points = []
    step = max(1, rect.width // 5)
    for x in range(rect.x, rect.right + 1, step):
        points.extend([(x, rect.bottom), (x + step // 2, rect.y), (x + step, rect.bottom)])
    pygame.draw.polygon(surface, (196, 102, 92), points)


def draw_energy_gate(surface, rect, anim_time=0.0, active=True):
    glow = pygame.Surface((rect.width + 48, rect.height + 28), pygame.SRCALPHA)
    intensity = 0.45 + 0.55 * math.sin(anim_time * 7.0)
    if active:
        pygame.draw.rect(glow, (96, 230, 255, int(76 + 45 * intensity)), (22, 10, rect.width + 4, rect.height + 8), border_radius=12)
        pygame.draw.rect(glow, (180, 255, 250, int(28 + 26 * intensity)), (16, 6, rect.width + 16, rect.height + 16), border_radius=14)
    surface.blit(glow, (rect.x - 22, rect.y - 10))
    frame_color = (72, 86, 106)
    pygame.draw.rect(surface, frame_color, rect.inflate(8, 0), width=4, border_radius=8)
    pygame.draw.rect(surface, (42, 48, 62), rect.inflate(0, 8), width=3, border_radius=8)
    if active:
        for step in range(5):
            y = rect.y + 8 + step * max(1, rect.height // 5)
            wave = math.sin(anim_time * 9.0 + step * 0.8) * 6
            pygame.draw.line(surface, (96, 234, 255), (rect.x + 3, y), (rect.right - 3, y + wave), 3)
        pygame.draw.rect(surface, (214, 252, 255), rect.inflate(-8, -8), width=2, border_radius=6)
    else:
        pygame.draw.rect(surface, (82, 88, 108), rect.inflate(-8, -8), width=2, border_radius=6)


def draw_bunker_crawler(surface, rect, anim_time=0.0, direction=1, burn=0.0):
    bob = math.sin(anim_time * 9.0) * 2
    body = rect.move(0, round(bob))
    shadow = pygame.Rect(body.x + 6, body.bottom - 4, body.width - 12, 8)
    pygame.draw.ellipse(surface, (0, 0, 0, 60), shadow)
    burn_t = clamp(burn / 1.35, 0, 1)
    shell_color = (
        int(60 * (1 - burn_t) + 144 * burn_t),
        int(84 * (1 - burn_t) + 112 * burn_t),
        int(78 * (1 - burn_t) + 62 * burn_t),
    )
    back_color = (
        int(95 * (1 - burn_t) + 214 * burn_t),
        int(132 * (1 - burn_t) + 176 * burn_t),
        int(122 * (1 - burn_t) + 94 * burn_t),
    )
    pygame.draw.ellipse(surface, shell_color, body)
    pygame.draw.ellipse(surface, back_color, body.inflate(-12, -10))
    eye_x = body.centerx + (7 if direction > 0 else -7)
    pygame.draw.circle(surface, (255, 208, 120), (eye_x, body.centery - 2), 4)
    pygame.draw.circle(surface, BLACK, (eye_x + (1 if direction > 0 else -1), body.centery - 2), 2)
    for index in range(4):
        leg_x = body.x + 7 + index * 10
        offset = math.sin(anim_time * 12 + index * 0.9) * 3
        pygame.draw.line(surface, (42, 54, 56), (leg_x, body.bottom - 2), (leg_x - 4, body.bottom + 5 + offset), 3)
        pygame.draw.line(surface, (42, 54, 56), (leg_x + 6, body.bottom - 2), (leg_x + 10, body.bottom + 5 - offset), 3)
    if burn_t > 0:
        glow = pygame.Surface((body.width + 24, body.height + 20), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 222, 148, int(26 + 42 * burn_t)), glow.get_rect())
        surface.blit(glow, (body.x - 12, body.y - 10))


def draw_bunker_wisp(surface, rect, anim_time=0.0):
    glow = pygame.Surface((rect.width + 44, rect.height + 44), pygame.SRCALPHA)
    pulse = 0.65 + 0.35 * math.sin(anim_time * 6.5)
    pygame.draw.circle(glow, (112, 240, 255, int(38 + 32 * pulse)), glow.get_rect().center, rect.width // 2 + 18)
    pygame.draw.circle(glow, (164, 255, 248, int(22 + 18 * pulse)), glow.get_rect().center, rect.width // 2 + 8)
    surface.blit(glow, (rect.x - 22, rect.y - 22))
    center = rect.center
    pygame.draw.circle(surface, (72, 218, 236), center, rect.width // 2)
    pygame.draw.circle(surface, (196, 255, 248), center, max(4, rect.width // 4))
    orbit = pygame.Vector2(math.sin(anim_time * 4.6), math.cos(anim_time * 4.6)) * (rect.width * 0.28)
    pygame.draw.circle(surface, (220, 255, 255), (round(center[0] + orbit.x), round(center[1] + orbit.y)), 3)


def draw_cipher_lamp(surface, rect, active=False, label=1):
    center = rect.center
    outer_r = rect.width // 2
    glow = pygame.Surface((rect.width + 48, rect.height + 48), pygame.SRCALPHA)
    if active:
        pygame.draw.circle(glow, (120, 238, 255, 62), glow.get_rect().center, outer_r + 18)
        pygame.draw.circle(glow, (255, 220, 150, 32), glow.get_rect().center, outer_r + 10)
    surface.blit(glow, (rect.x - 24, rect.y - 24))

    pygame.draw.circle(surface, (98, 84, 70), center, outer_r)
    pygame.draw.circle(surface, (156, 132, 102), center, outer_r - 4, 3)
    pygame.draw.circle(surface, (56, 66, 76), center, outer_r - 10)
    lens_color = (186, 244, 252) if active else (118, 154, 172)
    pygame.draw.circle(surface, lens_color, center, max(8, outer_r - 18))
    pygame.draw.circle(surface, (38, 48, 58), center, max(3, outer_r - 26))

    rune_y = rect.bottom + 8
    font = pygame.font.SysFont("consolas", 17, bold=True)
    text = font.render(str(label), True, (66, 42, 28))
    tag_rect = pygame.Rect(0, 0, 22, 18)
    tag_rect.center = (rect.centerx, rune_y)
    pygame.draw.rect(surface, (214, 194, 154), tag_rect, border_radius=5)
    pygame.draw.rect(surface, (122, 94, 62), tag_rect, 1, border_radius=5)
    surface.blit(text, (tag_rect.centerx - text.get_width() // 2, tag_rect.y - 1))


def draw_cipher_plate(surface, rect, active=False, label=1):
    base = (106, 86, 64) if active else (90, 78, 68)
    border = (228, 214, 184) if active else (168, 152, 128)
    glyph = (108, 220, 235) if active else (224, 212, 188)
    shadow = rect.move(0, 4)
    pygame.draw.rect(surface, (44, 34, 28), shadow, border_radius=8)
    pygame.draw.rect(surface, base, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, 2, border_radius=8)
    inner = rect.inflate(-14, -10)
    pygame.draw.rect(surface, (74, 58, 44), inner, border_radius=6)
    pygame.draw.line(surface, glyph, (inner.x + 10, inner.centery), (inner.right - 10, inner.centery), 2)
    pygame.draw.line(surface, glyph, (inner.centerx, inner.y + 5), (inner.centerx, inner.bottom - 5), 2)
    font = pygame.font.SysFont("consolas", 17, bold=True)
    text = font.render(str(label), True, (76, 52, 32))
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.y - 20))


def draw_cipher_seal(surface, rect, active=False, label=1):
    center = rect.center
    outer = 18
    inner = 10
    ring = (92, 228, 248) if active else (124, 106, 138)
    core = (26, 30, 42)
    wax = (154, 54, 58) if active else (104, 54, 66)
    glow = pygame.Surface((rect.width + 48, rect.height + 48), pygame.SRCALPHA)
    pygame.draw.circle(glow, (92, 228, 248, 46 if active else 18), glow.get_rect().center, outer + 14)
    surface.blit(glow, (rect.x - 24, rect.y - 24))

    pygame.draw.circle(surface, wax, center, outer - 2)
    pygame.draw.circle(surface, ring, center, outer, 3)
    pygame.draw.circle(surface, core, center, inner + 4)
    pygame.draw.circle(surface, ring, center, inner, 2)
    pygame.draw.line(surface, ring, (center[0] - outer + 4, center[1] - outer + 4), (center[0] + outer - 4, center[1] + outer - 4), 2)
    pygame.draw.line(surface, ring, (center[0] + outer - 4, center[1] - outer + 4), (center[0] - outer + 4, center[1] + outer - 4), 2)

    font = pygame.font.SysFont("consolas", 17, bold=True)
    text = font.render(str(label), True, (242, 234, 220))
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.bottom + 4))


def draw_cipher_marker(surface, rect, solved=False):
    shadow = rect.move(0, 4)
    pygame.draw.rect(surface, (18, 16, 18), shadow, border_radius=10)

    base = pygame.Rect(rect.x, rect.y, rect.width, rect.height)
    if solved:
        outer = (88, 162, 172)
        inner = (126, 204, 208)
        core = (210, 246, 242)
        glyph = (24, 66, 72)
    else:
        outer = (108, 92, 74)
        inner = (166, 140, 108)
        core = (222, 202, 160)
        glyph = (72, 48, 32)

    pygame.draw.rect(surface, outer, base, border_radius=10)
    pygame.draw.rect(surface, inner, base.inflate(-6, -6), border_radius=8)
    pygame.draw.rect(surface, core, base.inflate(-14, -14), border_radius=6)
    pygame.draw.rect(surface, glyph, base.inflate(-14, -14), 2, border_radius=6)

    center = base.center
    pygame.draw.circle(surface, glyph, center, 9, 2)
    pygame.draw.line(surface, glyph, (center[0] - 12, center[1]), (center[0] + 12, center[1]), 2)
    pygame.draw.line(surface, glyph, (center[0], center[1] - 12), (center[0], center[1] + 12), 2)
    pygame.draw.circle(surface, glyph, (center[0] - 13, center[1] - 13), 3)
    pygame.draw.circle(surface, glyph, (center[0] + 13, center[1] + 13), 3)
    pygame.draw.line(surface, (248, 238, 216, 180), (base.x + 8, base.y + 8), (base.right - 10, base.y + 8), 1)


def draw_boss_background(surface, distortion):
    for y in range(HEIGHT):
        wave_offset = math.sin(y * 0.035 + pygame.time.get_ticks() * 0.004) * 18 * distortion
        blend = y / HEIGHT
        color = (
            int(17 * (1 - blend) + 6 * blend + distortion * 40),
            int(17 * (1 - blend) + 13 * blend),
            int(32 * (1 - blend) + 44 * blend + abs(wave_offset)),
        )
        pygame.draw.line(surface, color, (wave_offset, y), (WIDTH + wave_offset, y))
    for _ in range(7):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        pygame.draw.circle(surface, (40, 30, 60), (x, y), random.randint(70, 130), 1)


def draw_bill_shadow(surface, rect, health):
    pulse = 1 + 0.04 * math.sin(pygame.time.get_ticks() * 0.01)
    center = rect.center
    points = [(center[0], rect.y), (rect.x, rect.bottom), (rect.right, rect.bottom)]
    scaled = []
    for px, py in points:
        scaled.append((center[0] + (px - center[0]) * pulse, center[1] + (py - center[1]) * pulse))
    pygame.draw.polygon(surface, (28, 18, 34), scaled)
    pygame.draw.polygon(surface, AMBER, scaled, 4)
    pygame.draw.circle(surface, WHITE, (center[0], rect.y + 72), 18)
    pygame.draw.circle(surface, BLACK, (center[0] - 6, rect.y + 72), 3)
    pygame.draw.circle(surface, BLACK, (center[0] + 6, rect.y + 72), 3)
    pygame.draw.line(surface, BLACK, (center[0] - 10, rect.y + 88), (center[0] + 10, rect.y + 80), 2)
    pygame.draw.line(surface, BLACK, (rect.x + 28, rect.bottom - 8), (rect.x - 16, rect.bottom + 36), 4)
    pygame.draw.line(surface, BLACK, (rect.right - 28, rect.bottom - 8), (rect.right + 16, rect.bottom + 36), 4)
    pygame.draw.line(surface, BLACK, (center[0], rect.y + 40), (center[0], rect.bottom - 24), 4)
    pygame.draw.line(surface, BLACK, (center[0] - 36, rect.y + 120), (center[0] + 36, rect.y + 106), 4)
    for i in range(max(0, health)):
        pygame.draw.line(surface, (255, 215, 130), (rect.x + 8 + i * 12, rect.bottom + 24), (rect.x + 16 + i * 12, rect.bottom + 24), 4)


def build_dark_energy_points(projectile, camera_x=0):
    direction = projectile["dir"]
    normal = pygame.Vector2(-direction.y, direction.x)
    length = projectile["travel"]
    anim_time = projectile["anim_time"]
    points = []
    segments = 8
    for index in range(segments + 1):
        t = index / segments
        along = projectile["origin"] + direction * (length * t)
        wave = math.sin(anim_time * projectile["wave_speed"] + t * projectile["wave_freq"] + projectile["phase"])
        offset = normal * (wave * projectile["wave_amp"] * (0.2 + 0.8 * t))
        point = along + offset
        points.append((round(point.x - camera_x), round(point.y)))
    return points


def draw_dark_energy_stream(surface, projectile, camera_x=0):
    points = build_dark_energy_points(projectile, camera_x)
    if len(points) < 2:
        return
    glow = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    outer_width = max(15, projectile["width"] + 12)
    mid_width = max(9, projectile["width"] + 5)
    core_width = max(4, projectile["width"] - 2)
    pygame.draw.lines(glow, (18, 8, 28, 125), False, points, outer_width)
    pygame.draw.lines(glow, (34, 12, 52, 94), False, points, mid_width)
    surface.blit(glow, (0, 0))
    pygame.draw.lines(surface, (12, 6, 20), False, points, outer_width - 4)
    pygame.draw.lines(surface, (36, 14, 58), False, points, mid_width)
    pygame.draw.lines(surface, (84, 44, 128), False, points, core_width)
    head = points[0]
    pygame.draw.circle(surface, (28, 10, 44), head, max(8, projectile["width"] + 2))
    pygame.draw.circle(surface, (94, 48, 146), head, max(4, projectile["width"] // 2))


def draw_attack_telegraph(surface, attack, timer, camera_x=0):
    points = build_dark_energy_points(attack, camera_x)
    if len(points) < 2:
        return
    pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() * 0.018)
    width = max(10, attack["width"] + 8)
    warn = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.lines(warn, (255, 96, 126, int(58 + 56 * pulse)), False, points, width)
    pygame.draw.lines(warn, (255, 214, 130, int(34 + 42 * pulse)), False, points, max(3, width // 3))
    surface.blit(warn, (0, 0))
    head = points[-1]
    pygame.draw.circle(surface, (255, 120, 138), head, max(6, attack["width"]))
    pygame.draw.circle(surface, (255, 238, 184), head, max(2, attack["width"] // 3))


def draw_ground_attack_telegraph(surface, warning, camera_x=0):
    pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() * 0.016 + warning["phase"])
    width = warning["width"]
    x = round(warning["x"] - camera_x)
    base_rect = pygame.Rect(x - width, GROUND_Y - 22, width * 2, 26)
    glow = pygame.Surface((base_rect.width + 36, base_rect.height + 22), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (255, 82, 110, int(48 + 44 * pulse)), glow.get_rect())
    surface.blit(glow, (base_rect.x - 18, base_rect.y - 10))
    pygame.draw.ellipse(surface, (255, 110, 136), base_rect, 3)
    inner = base_rect.inflate(-18, -10)
    pygame.draw.ellipse(surface, (255, 222, 148), inner, 2)


def draw_portal(surface, rect, charge):
    glow = pygame.Surface((rect.width + 70, rect.height + 70), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (74, 190, 255, 50 + int(charge * 100)), glow.get_rect(), width=24)
    surface.blit(glow, (rect.x - 35, rect.y - 35))
    pygame.draw.ellipse(surface, (85, 173, 255), rect, 5)
    inner = rect.inflate(-26, -32)
    pygame.draw.ellipse(surface, (18, 36, 66), inner)
    active = inner.inflate(-22, -22)
    fill_height = int(active.height * clamp(charge, 0, 1))
    if fill_height > 0:
        pygame.draw.ellipse(surface, (93, 220, 255), (active.x, active.bottom - fill_height, active.width, fill_height))


def draw_stan(surface, rect):
    pygame.draw.rect(surface, (50, 55, 71), (rect.x + 10, rect.y + 18, 26, 44), border_radius=6)
    pygame.draw.rect(surface, (31, 34, 47), (rect.x + 8, rect.y + 62, 10, 20), border_radius=3)
    pygame.draw.rect(surface, (31, 34, 47), (rect.x + 28, rect.y + 62, 10, 20), border_radius=3)
    pygame.draw.rect(surface, (231, 199, 163), (rect.x + 11, rect.y, 24, 22), border_radius=10)
    pygame.draw.rect(surface, CRIMSON, (rect.x + 16, rect.y + 26, 14, 18))
    pygame.draw.lines(surface, AMBER, False, [(rect.right + 4, rect.y + 32), (rect.right + 20, rect.y + 32), (rect.right + 24, rect.y + 38), (rect.right + 10, rect.y + 38)], 3)
    pygame.draw.circle(surface, AMBER, (rect.right + 1, rect.y + 35), 6, 2)


def draw_hud(surface, fonts, player, collected, total, level_index, message):
    panel = pygame.Rect(16, 10, WIDTH - 32, 104)
    draw_note_panel(surface, panel, pin_color=(160, 50, 44), alpha=214)
    title_color = (58, 32, 18)
    body_color = (68, 42, 24)
    accent_color = (98, 62, 28)
    header_font = fonts.get("body", fonts["tiny"])
    meta_font = fonts.get("micro", fonts["tiny"])
    surface.blit(header_font.render(f"Journal {level_index}", True, title_color), (34, 18))
    surface.blit(header_font.render(f"Pages: {collected}/{total}", True, body_color), (34, 48))
    for i in range(player.max_health):
        color = (182, 54, 44) if i < player.health else (128, 98, 86)
        x = 270 + i * 28
        pygame.draw.rect(surface, color, (x, 22, 20, 20), border_radius=6)
        pygame.draw.rect(surface, (108, 62, 44), (x, 22, 20, 20), 2, border_radius=6)
    surface.blit(meta_font.render("Lens energy", True, accent_color), (270, 56))
    pygame.draw.rect(surface, (126, 98, 76), (392, 57, 188, 12), border_radius=6)
    pygame.draw.rect(surface, (214, 174, 88), (392, 57, int(188 * player.reveal_energy / player.max_reveal), 12), border_radius=6)
    pygame.draw.rect(surface, (134, 96, 52), (392, 57, 188, 12), 2, border_radius=6)
    message_lines = render_wrapped_lines(meta_font, message, body_color, 500)
    text_y = 20
    for line in message_lines[:2]:
        surface.blit(line, (620, text_y))
        text_y += line.get_height() + 6


def render_wrapped_lines(font, text, color, max_width):
    words = text.split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(font.render(current, True, color))
            current = word
    lines.append(font.render(current, True, color))
    return lines


def draw_note_panel(surface, rect, pin_color=(182, 48, 44), alpha=228):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (228, 206, 164, alpha), panel.get_rect(), border_radius=18)
    pygame.draw.rect(panel, (145, 104, 72, alpha), panel.get_rect(), 3, border_radius=18)
    inner = panel.get_rect().inflate(-14, -14)
    pygame.draw.rect(panel, (242, 226, 192, 70), inner, 1, border_radius=14)
    for x in range(16, rect.width - 16, 34):
        pygame.draw.line(panel, (255, 244, 220, 18), (x, 14), (x + 12, rect.height - 14), 1)
    for px, py in ((18, 18), (rect.width - 28, 18), (26, rect.height - 24)):
        pygame.draw.circle(panel, pin_color + (alpha,), (px, py), 5)
        pygame.draw.circle(panel, (255, 224, 176, alpha), (px - 1, py - 1), 2)
    surface.blit(panel, rect.topleft)


def draw_note_chip(surface, rect, text, font, text_color=(86, 56, 34), pin=False):
    draw_note_panel(surface, rect, pin_color=(160, 50, 44) if pin else (148, 94, 62), alpha=216)
    rendered = font.render(text, True, text_color)
    surface.blit(rendered, (rect.centerx - rendered.get_width() // 2, rect.centery - rendered.get_height() // 2))


class Game:
    def __init__(self):
        pygame.init()
        self.music_enabled = True
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2)
        except pygame.error:
            self.music_enabled = False
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.asset_paths = {
            "menu_background": first_existing(os.path.join(IMAGES_DIR, "menu_background.png"), os.path.join(IMAGES_DIR, "menu_background.jpg")),
            "menu_logo": first_existing(
                os.path.join(IMAGES_DIR, "menu_logo.png"),
                os.path.join(IMAGES_DIR, "menu_logo.jpg"),
                os.path.join(IMAGES_DIR, "logo.png"),
                os.path.join(IMAGES_DIR, "logo.jpg"),
            ),
            "settings_background": first_existing(os.path.join(IMAGES_DIR, "settings_background.png"), os.path.join(IMAGES_DIR, "settings_background.jpg")),
            "cipher_background": first_existing(os.path.join(IMAGES_DIR, "cipher_background.png"), os.path.join(IMAGES_DIR, "cipher_background.jpg")),
            "forest_background": first_existing(os.path.join(IMAGES_DIR, "forest_background.png"), os.path.join(IMAGES_DIR, "forest_background.jpg")),
            "bunker_background": first_existing(os.path.join(IMAGES_DIR, "bunker_background.png"), os.path.join(IMAGES_DIR, "bunker_background.jpg")),
            "bunker_tileset": first_existing(os.path.join(IMAGES_DIR, "bunker_tileset.png"), os.path.join(IMAGES_DIR, "bunker_tileset.jpg")),
            "boss_background": first_existing(os.path.join(IMAGES_DIR, "boss_background.png"), os.path.join(IMAGES_DIR, "boss_background.jpg")),
            "button": first_existing(os.path.join(IMAGES_DIR, "button.png"), os.path.join(IMAGES_DIR, "button_idle.png")),
            "button_hover": first_existing(os.path.join(IMAGES_DIR, "button_hover.png"), os.path.join(IMAGES_DIR, "button_active.png")),
            "settings_panel": first_existing(os.path.join(IMAGES_DIR, "settings_panel.png")),
            "settings_row": first_existing(os.path.join(IMAGES_DIR, "settings_row.png")),
            "settings_row_active": first_existing(os.path.join(IMAGES_DIR, "settings_row_active.png")),
            "settings_slider_bar": first_existing(os.path.join(IMAGES_DIR, "settings_slider_bar.png")),
            "settings_slider_fill": first_existing(os.path.join(IMAGES_DIR, "settings_slider_fill.png")),
            "settings_slider_knob": first_existing(os.path.join(IMAGES_DIR, "settings_slider_knob.png")),
            "settings_arrow_left": first_existing(os.path.join(IMAGES_DIR, "settings_arrow_left.png")),
            "settings_arrow_right": first_existing(os.path.join(IMAGES_DIR, "settings_arrow_right.png")),
            "settings_difficulty": first_existing(os.path.join(IMAGES_DIR, "settings_difficulty.png")),
            "fullscreen_button": first_existing(os.path.join(IMAGES_DIR, "fullscreen_button_idle.png")),
            "fullscreen_button_hover": first_existing(os.path.join(IMAGES_DIR, "fullscreen_button_hover.png")),
            "music_toggle_on": first_existing(os.path.join(IMAGES_DIR, "music_toggle_on.png"), os.path.join(IMAGES_DIR, "music_on_idle.png")),
            "music_toggle_on_hover": first_existing(os.path.join(IMAGES_DIR, "music_toggle_on_hover.png"), os.path.join(IMAGES_DIR, "music_on_hover.png")),
            "music_toggle_off": first_existing(os.path.join(IMAGES_DIR, "music_toggle_off.png"), os.path.join(IMAGES_DIR, "music_off_idle.png")),
            "music_toggle_off_hover": first_existing(os.path.join(IMAGES_DIR, "music_toggle_off_hover.png"), os.path.join(IMAGES_DIR, "music_off_hover.png")),
            "player_idle": first_existing(os.path.join(IMAGES_DIR, "player_idle.png"), os.path.join(IMAGES_DIR, "dipper_idle.png")),
            "player_run_1": first_existing(os.path.join(IMAGES_DIR, "player_run_1.png"), os.path.join(IMAGES_DIR, "dipper_run_1.png"), os.path.join(IMAGES_DIR, "player_run1.png")),
            "player_run_2": first_existing(os.path.join(IMAGES_DIR, "player_run_2.png"), os.path.join(IMAGES_DIR, "dipper_run_2.png"), os.path.join(IMAGES_DIR, "player_run2.png")),
            "player_run_3": first_existing(os.path.join(IMAGES_DIR, "player_run_3.png"), os.path.join(IMAGES_DIR, "dipper_run_3.png"), os.path.join(IMAGES_DIR, "player_run3.png")),
            "player_run_4": first_existing(os.path.join(IMAGES_DIR, "player_run_4.png"), os.path.join(IMAGES_DIR, "dipper_run_4.png"), os.path.join(IMAGES_DIR, "player_run4.png")),
            "boss_idle": first_existing(os.path.join(IMAGES_DIR, "boss_idle.png")),
            "gnome_idle": first_existing(os.path.join(IMAGES_DIR, "gnome_idle.png")),
            "gnome_run_1": first_existing(os.path.join(IMAGES_DIR, "gnome_run_1.png")),
            "gnome_run_2": first_existing(os.path.join(IMAGES_DIR, "gnome_run_2.png")),
            "gnome_run_3": first_existing(os.path.join(IMAGES_DIR, "gnome_run_3.png")),
            "gnome_run_4": first_existing(os.path.join(IMAGES_DIR, "gnome_run_4.png")),
            "music": first_existing(
                os.path.join(AUDIO_DIR, "menu_music.ogg"),
                os.path.join(AUDIO_DIR, "menu_music.mp3"),
                os.path.join(AUDIO_DIR, "menu_music.wav"),
                os.path.join(AUDIO_DIR, "bg_music.ogg"),
                os.path.join(AUDIO_DIR, "bg_music.mp3"),
                os.path.join(AUDIO_DIR, "bg_music.wav"),
            ),
            "font_title": first_existing(os.path.join(FONTS_DIR, "AvenuePixelSoft-Stroke-Regular.ttf")),
            "font_ui": first_existing(os.path.join(FONTS_DIR, "AvenuePixel-Regular.ttf")),
            "font_mono": first_existing(os.path.join(FONTS_DIR, "AvenuePixelSoft-Stroke-Regular.ttf")),
        }
        self.fonts = {
            "title": load_font(self.asset_paths["font_title"], 44, "georgia", bold=True),
            "small": load_font(self.asset_paths["font_ui"], 44, "georgia", bold=True),
            "tiny": load_font(self.asset_paths["font_mono"], 28, "consolas"),
            "body": load_font(self.asset_paths["font_ui"], 24, "georgia", bold=True),
            "micro": load_font(self.asset_paths["font_mono"], 18, "consolas"),
        }
        self.level_factories = [ForestLevel, BunkerLevel, BossLevel]
        self.state = "menu"
        self.levels = self.build_levels()
        self.bunker_bonuses = set()
        self.true_ending = False
        self.active_cipher_id = None
        self.cipher_modal_message = ""
        self.cipher_modal_message_timer = 0.0
        self.level_index = self.load_progress()
        self.banner_timer = 4.0
        self.overlay_text = f"Level {self.level_index + 1}"
        self.death_timer = 0.0
        self.death_message = ""
        self.menu_buttons = {}
        self.pause_buttons = {}
        self.volume = 0.42
        self.settings_area = pygame.Rect(620, 135, 435, 458)
        self.volume_slider_rect = pygame.Rect(0, 0, 300, 12)
        self.dragging_volume = False
        self.fullscreen = False
        self.difficulty_options = ["Easy", "Normal", "Hard"]
        self.difficulty_index = 1
        self.settings_return_state = "menu"
        self.settings_buttons = {
            "music": pygame.Rect(0, 0, 360, 46),
            "fullscreen": pygame.Rect(0, 0, 360, 46),
            "difficulty_left": pygame.Rect(0, 0, 52, 46),
            "difficulty_value": pygame.Rect(0, 0, 236, 46),
            "difficulty_right": pygame.Rect(0, 0, 52, 46),
            "main_menu": pygame.Rect(0, 0, 360, 46),
        }
        self.ui_images = {
            "menu_background": load_scaled_image(self.asset_paths["menu_background"], (WIDTH, HEIGHT)),
            "menu_logo": trim_transparent_bounds(load_image(self.asset_paths["menu_logo"])),
            "settings_background": load_scaled_image(self.asset_paths["settings_background"], (WIDTH, HEIGHT)),
            "cipher_background": load_image(self.asset_paths["cipher_background"]),
        }
        self.level_backgrounds = {
            "forest": load_image(self.asset_paths["forest_background"]),
            "bunker": load_image(self.asset_paths["bunker_background"]),
            "bunker_tileset": load_image(self.asset_paths["bunker_tileset"]),
            "boss": load_image(self.asset_paths["boss_background"]),
            "forest_layers": load_parallax_layers("forest", 12),
            "bunker_layers": load_parallax_layers("bunker", 12),
        }
        Player.set_sprites(
            load_image(self.asset_paths["player_idle"]),
            [
                load_image(self.asset_paths["player_run_1"]),
                load_image(self.asset_paths["player_run_2"]),
                load_image(self.asset_paths["player_run_3"]),
                load_image(self.asset_paths["player_run_4"]),
            ],
        )
        BossLevel.set_sprite(load_image(self.asset_paths["boss_idle"]))
        GnomeSprite.set_sprites(
            load_image(self.asset_paths["gnome_idle"]),
            [
                load_image(self.asset_paths["gnome_run_1"]),
                load_image(self.asset_paths["gnome_run_2"]),
                load_image(self.asset_paths["gnome_run_3"]),
                load_image(self.asset_paths["gnome_run_4"]),
            ],
        )
        self.button_images = {
            "idle": trim_transparent_bounds(load_image(self.asset_paths["button"])),
            "hover": trim_transparent_bounds(load_image(self.asset_paths["button_hover"])) or trim_transparent_bounds(load_image(self.asset_paths["button"])),
        }
        self.fullscreen_button_images = {
            "idle": trim_transparent_bounds(load_image(self.asset_paths["fullscreen_button"])) or self.button_images["idle"],
            "hover": trim_transparent_bounds(load_image(self.asset_paths["fullscreen_button_hover"])) or trim_transparent_bounds(load_image(self.asset_paths["fullscreen_button"])) or self.button_images["hover"] or self.button_images["idle"],
        }
        self.settings_images = {
            "panel": load_image(self.asset_paths["settings_panel"]),
            "row": load_image(self.asset_paths["settings_row"]),
            "row_active": load_image(self.asset_paths["settings_row_active"]) or load_image(self.asset_paths["settings_row"]),
            "slider_bar": trim_transparent_bounds(load_image(self.asset_paths["settings_slider_bar"])),
            "slider_fill": trim_transparent_bounds(load_image(self.asset_paths["settings_slider_fill"])),
            "slider_knob": trim_transparent_bounds(load_image(self.asset_paths["settings_slider_knob"])),
            "arrow_left": load_image(self.asset_paths["settings_arrow_left"]),
            "arrow_right": load_image(self.asset_paths["settings_arrow_right"]),
            "difficulty": load_image(self.asset_paths["settings_difficulty"]),
            "music_toggle_on": load_image(self.asset_paths["music_toggle_on"]),
            "music_toggle_on_hover": load_image(self.asset_paths["music_toggle_on_hover"]) or load_image(self.asset_paths["music_toggle_on"]),
            "music_toggle_off": load_image(self.asset_paths["music_toggle_off"]),
            "music_toggle_off_hover": load_image(self.asset_paths["music_toggle_off_hover"]) or load_image(self.asset_paths["music_toggle_off"]),
        }
        self.rebuild_settings_layout()
        self.load_sfx()
        self.start_music()
        self.apply_difficulty()
        self.apply_bunker_bonuses_to_levels()
        self.mouse_locked = False

    def build_levels(self):
        return [factory() for factory in self.level_factories]

    def apply_bunker_bonuses_to_levels(self):
        for level in self.levels:
            if isinstance(level, BossLevel):
                level.apply_bunker_bonuses(self.bunker_bonuses)

    def load_progress(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as save_file:
                data = json.load(save_file)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return 0
        try:
            saved_level = int(data.get("level_index", 0))
        except (TypeError, ValueError):
            return 0
        return clamp(saved_level, 0, len(self.level_factories) - 1)

    def save_progress(self):
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as save_file:
                json.dump({"level_index": self.level_index}, save_file)
        except OSError:
            pass

    def clear_progress(self):
        try:
            if os.path.exists(SAVE_FILE):
                os.remove(SAVE_FILE)
        except OSError:
            pass

    def start_music(self):
        if not self.music_enabled:
            return
        try:
            pygame.mixer.music.load(self.asset_paths["music"] or make_music())
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1)
        except pygame.error:
            self.music_enabled = False

    def load_sfx(self):
        global SFX_SOUNDS
        if not pygame.mixer.get_init():
            SFX_SOUNDS = {}
            return
        SFX_SOUNDS = {
            "jump": load_sfx_sound("jump", 0.4),
            "page": load_sfx_sound("page", 0.42),
            "hit": load_sfx_sound("hit", 0.48),
            "cipher_open": load_sfx_sound("cipher_open", 0.45),
            "cipher_solve": load_sfx_sound("cipher_solve", 0.48),
            "burn": load_sfx_sound("burn", 0.4),
            "boss_teleport": load_sfx_sound("boss_teleport", 0.46),
            "boss_attack": load_sfx_sound("boss_attack", 0.4),
            "portal": load_sfx_sound("portal", 0.5),
            "menu": load_sfx_sound("menu", 0.32),
        }

    def set_volume_from_pos(self, mouse_x):
        left, right = self.get_slider_inner_bounds()
        self.volume = clamp((mouse_x - left) / max(1, right - left), 0.0, 1.0)
        if self.music_enabled:
            pygame.mixer.music.set_volume(self.volume)

    def rebuild_settings_layout(self):
        area = self.settings_area
        content_left = area.x + 54
        content_right = area.right - 6
        content_width = content_right - content_left
        content_top = area.y + 62
        content_bottom = area.bottom - 12
        section_gap = 12

        fullscreen_label_w = max(
            self.fonts["small"].size("Fullscreen: On")[0],
            self.fonts["small"].size("Fullscreen: Off")[0],
        )
        if self.fullscreen_button_images["idle"]:
            fullscreen_box = (int(clamp(content_width, fullscreen_label_w + 220, content_width)), 190)
            fullscreen_w, fullscreen_h = fit_size(self.fullscreen_button_images["idle"].get_size(), fullscreen_box)
        else:
            fullscreen_w, fullscreen_h = content_width, 82
        fullscreen_x = content_left + max(0, (content_width - fullscreen_w) // 2)
        fullscreen_y = content_top
        self.settings_buttons["fullscreen"] = pygame.Rect(fullscreen_x, fullscreen_y, fullscreen_w, fullscreen_h)

        difficulty_y = fullscreen_y + fullscreen_h + section_gap
        arrow_w = 52
        arrow_h = 46
        arrow_gap = 10
        diff_value_x = content_left + arrow_w + arrow_gap
        diff_value_w = content_width - (arrow_w * 2) - (arrow_gap * 2)
        self.settings_buttons["difficulty_left"] = pygame.Rect(content_left, difficulty_y, arrow_w, arrow_h)
        self.settings_buttons["difficulty_value"] = pygame.Rect(diff_value_x, difficulty_y, diff_value_w, arrow_h)
        self.settings_buttons["difficulty_right"] = pygame.Rect(content_right - arrow_w, difficulty_y, arrow_w, arrow_h)

        menu_button_y = difficulty_y + arrow_h + section_gap
        if self.button_images["idle"]:
            menu_w, menu_h = fit_size(self.button_images["idle"].get_size(), (content_width, 104))
        else:
            menu_w, menu_h = content_width, 58
        menu_x = content_left + max(0, (content_width - menu_w) // 2)
        self.settings_buttons["main_menu"] = pygame.Rect(menu_x, menu_button_y, menu_w, menu_h)

        music_size = self.get_music_toggle_reference_size()
        slider_gap = 10
        slider_label_gap = 36
        music_row_top = self.settings_buttons["main_menu"].bottom + 18
        available_group_height = max(86, content_bottom - music_row_top)
        music_max_h = int(clamp(available_group_height, 86, 116))
        if music_size:
            music_w, music_h = fit_size(music_size, (250, music_max_h))
        else:
            music_w, music_h = 250, min(96, music_max_h)
        slider_w = max(150, content_width - music_w - slider_gap)
        slider_bar_image = crop_visible_bounds(self.settings_images["slider_bar"])
        if slider_bar_image:
            slider_ratio = slider_bar_image.get_width() / max(1, slider_bar_image.get_height())
            slider_h = int(clamp(slider_w / max(slider_ratio, 0.1), 22, 32))
        else:
            slider_h = 22

        slider_total_h = slider_h + slider_label_gap
        bottom_group_h = min(max(music_h, slider_total_h), available_group_height)
        combined_w = music_w + slider_gap + slider_w
        bottom_left = content_left + max(0, (content_width - combined_w) // 2)
        music_y = music_row_top + max(0, (bottom_group_h - music_h) // 2)
        slider_y = music_row_top + slider_label_gap
        self.settings_buttons["music"] = pygame.Rect(bottom_left, music_y, music_w, music_h)
        self.volume_slider_rect = pygame.Rect(bottom_left + music_w + slider_gap, slider_y, slider_w, slider_h)


    def get_music_toggle_reference_size(self):
        variants = [
            self.settings_images["music_toggle_on"],
            self.settings_images["music_toggle_on_hover"],
            self.settings_images["music_toggle_off"],
            self.settings_images["music_toggle_off_hover"],
        ]
        variants = [image for image in variants if image is not None]
        if not variants:
            return None
        max_w = max(image.get_width() for image in variants)
        max_h = max(image.get_height() for image in variants)
        return max_w, max_h

    def get_slider_visual_rect(self):
        return self.volume_slider_rect.inflate(18, 0)

    def get_slider_inner_bounds(self):
        visual_rect = self.get_slider_visual_rect()
        edge_padding = max(10, visual_rect.height // 2)
        return visual_rect.left + edge_padding, visual_rect.right - edge_padding

    def apply_difficulty(self):
        settings = {
            0: {"health": 7, "reveal": 6.4, "forest_spawn_scale": 1.18},
            1: {"health": 5, "reveal": 5.5, "forest_spawn_scale": 1.0},
            2: {"health": 4, "reveal": 4.7, "forest_spawn_scale": 0.86},
        }
        config = settings[self.difficulty_index]
        for level in self.levels:
            self.apply_difficulty_to_level(level, config)

    def apply_difficulty_to_level(self, level, config):
        player = level.player
        if isinstance(level, BossLevel):
            player.max_health = max(config["health"], 5)
            player.health = min(player.health, player.max_health)
        else:
            player.max_health = config["health"]
            player.health = min(player.health, player.max_health)
        player.max_reveal = config["reveal"]
        player.reveal_energy = min(player.reveal_energy, player.max_reveal)
        if isinstance(level, ForestLevel):
            level.spawn_scale = config["forest_spawn_scale"]

    def toggle_music(self):
        if not pygame.mixer.get_init():
            self.music_enabled = False
            return
        play_sfx("menu")
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            self.start_music()
        else:
            pygame.mixer.music.stop()

    def toggle_fullscreen(self):
        play_sfx("menu")
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
        self.update_mouse_lock(force=True)

    def should_lock_mouse(self):
        return self.state == "playing"

    def force_center_mouse(self):
        if not self.mouse_locked:
            return
        center = (WIDTH // 2, HEIGHT // 2)
        pygame.mouse.set_pos(center)
        if hasattr(pygame.mouse, "get_rel"):
            pygame.mouse.get_rel()

    def update_mouse_lock(self, force=False):
        lock_mouse = self.should_lock_mouse()
        if force or lock_mouse != self.mouse_locked:
            if hasattr(pygame.mouse, "set_relative_mode"):
                try:
                    pygame.mouse.set_relative_mode(lock_mouse)
                except pygame.error:
                    pass
            pygame.event.set_grab(lock_mouse)
            pygame.mouse.set_visible(not lock_mouse)
            self.mouse_locked = lock_mouse
        if lock_mouse:
            self.force_center_mouse()

    def reset_level(self, index=None):
        target_index = self.level_index if index is None else index
        self.levels[target_index] = self.level_factories[target_index]()
        settings = {
            0: {"health": 7, "reveal": 6.4, "forest_spawn_scale": 1.18},
            1: {"health": 5, "reveal": 5.5, "forest_spawn_scale": 1.0},
            2: {"health": 4, "reveal": 4.7, "forest_spawn_scale": 0.86},
        }
        self.apply_difficulty_to_level(self.levels[target_index], settings[self.difficulty_index])
        if isinstance(self.levels[target_index], BossLevel):
            self.levels[target_index].apply_bunker_bonuses(self.bunker_bonuses)

    def restart_all(self, clear_save=True):
        self.levels = self.build_levels()
        self.bunker_bonuses = set()
        self.true_ending = False
        self.active_cipher_id = None
        self.cipher_modal_message = ""
        self.cipher_modal_message_timer = 0.0
        self.level_index = 0
        self.state = "menu"
        self.overlay_text = "Level 1"
        self.banner_timer = 4.0
        self.death_timer = 0.0
        self.death_message = ""
        self.settings_return_state = "menu"
        self.apply_difficulty()
        self.apply_bunker_bonuses_to_levels()
        if clear_save:
            self.clear_progress()

    def start_death_restart(self):
        self.state = "death_notice"
        self.death_timer = 2.0
        self.death_message = f"You died. Restarting level {self.level_index + 1}..."

    def finish_death_restart(self):
        self.reset_level(self.level_index)
        self.state = "playing"
        self.update_mouse_lock(force=True)
        self.overlay_text = f"Level {self.level_index + 1}"
        self.banner_timer = 2.2

    def start_new_game(self):
        self.levels = self.build_levels()
        self.bunker_bonuses = set()
        self.true_ending = False
        self.active_cipher_id = None
        self.cipher_modal_message = ""
        self.cipher_modal_message_timer = 0.0
        self.level_index = 0
        self.apply_difficulty()
        self.apply_bunker_bonuses_to_levels()
        self.clear_progress()
        self.state = "playing"
        self.update_mouse_lock(force=True)
        self.overlay_text = "Level 1"
        self.banner_timer = 3.0
        self.death_timer = 0.0
        self.death_message = ""
        self.settings_return_state = "menu"

    def continue_game(self):
        self.level_index = self.load_progress()
        self.levels = self.build_levels()
        self.bunker_bonuses = set()
        self.true_ending = False
        self.active_cipher_id = None
        self.cipher_modal_message = ""
        self.cipher_modal_message_timer = 0.0
        self.apply_difficulty()
        self.apply_bunker_bonuses_to_levels()
        self.state = "playing"
        self.update_mouse_lock(force=True)
        self.overlay_text = f"Level {self.level_index + 1}"
        self.banner_timer = 3.0
        self.death_timer = 0.0
        self.death_message = ""
        self.settings_return_state = "menu"

    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"
        self.update_mouse_lock(force=True)

    def draw_death_notice(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 190))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 320, 180, 640, 220)
        draw_note_panel(self.screen, panel, pin_color=(134, 34, 30), alpha=224)
        title = self.fonts["title"].render("You Died", True, (116, 34, 26))
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 34))
        subtitle = self.fonts["small"].render(self.death_message, True, (88, 60, 40))
        self.screen.blit(subtitle, (panel.centerx - subtitle.get_width() // 2, panel.y + 118))

    @property
    def current_level(self):
        return self.levels[self.level_index]

    def get_menu_button_size(self):
        if self.button_images["idle"]:
            ratio = self.button_images["idle"].get_width() / max(1, self.button_images["idle"].get_height())
            max_label_width = 0
            for label in ("Continue", "Play", "Settings", "Exit", "Main Menu"):
                max_label_width = max(max_label_width, self.fonts["small"].size(label)[0])
            target_width = max(314, int((max_label_width + 120) * 1.12))
            target_width = int(clamp(target_width, 314, 515))
            target_height = int(target_width / max(ratio, 0.1))
            return target_width, int(clamp(target_height, 100, 162))
        return 336, 76

    def build_vertical_button_layout(self, labels, area):
        button_w, button_h = self.get_menu_button_size()
        gap = 16 if self.button_images["idle"] else 12
        available_height = area.height
        available_width = area.width
        visual_bounds = self.get_button_visual_bounds((button_w, button_h))
        visible_step = visual_bounds.height + gap
        total_height = visual_bounds.top + visual_bounds.height * len(labels) + gap * max(0, len(labels) - 1) + (button_h - visual_bounds.bottom)
        if total_height > available_height:
            button_h = max(72, (available_height - gap * max(0, len(labels) - 1)) // max(1, len(labels)))
            if self.button_images["idle"]:
                ratio = self.button_images["idle"].get_width() / max(1, self.button_images["idle"].get_height())
                button_w = int(clamp(button_h * ratio, 240, min(460, available_width)))
            visual_bounds = self.get_button_visual_bounds((button_w, button_h))
            visible_step = visual_bounds.height + gap
            total_height = visual_bounds.top + visual_bounds.height * len(labels) + gap * max(0, len(labels) - 1) + (button_h - visual_bounds.bottom)
        button_w = min(button_w, available_width)
        start_x = area.x + max(0, (available_width - button_w) // 2)
        start_y = area.y + max(0, (available_height - total_height) // 2)
        buttons = {}
        for index, (key, label) in enumerate(labels):
            rect = pygame.Rect(start_x, start_y + index * visible_step, button_w, button_h)
            buttons[key] = {"rect": rect, "label": label}
        return buttons

    def get_button_surface_and_rect(self, key, hovered, state="menu"):
        button = self.get_button_collection(state)[key]
        source = self.button_images["hover"] if hovered else self.button_images["idle"]
        if not source:
            return None, button["rect"]
        scaled = pygame.transform.smoothscale(source, button["rect"].size)
        draw_rect = scaled.get_rect(center=button["rect"].center)
        return scaled, draw_rect

    def get_button_visual_bounds(self, size):
        source = self.button_images["idle"]
        if not source:
            return pygame.Rect(0, 0, size[0], size[1])
        scaled = pygame.transform.smoothscale(source, size)
        bounds = scaled.get_bounding_rect(min_alpha=20)
        if bounds.width <= 0 or bounds.height <= 0:
            return pygame.Rect(0, 0, size[0], size[1])
        return bounds

    def is_point_on_button_texture(self, key, point, state="menu"):
        if not self.button_images["idle"]:
            return self.get_button_collection(state)[key]["rect"].collidepoint(point)
        surface, rect = self.get_button_surface_and_rect(key, False, state)
        if not surface or not rect.collidepoint(point):
            return False
        local_x = point[0] - rect.x
        local_y = point[1] - rect.y
        try:
            return surface.get_at((local_x, local_y)).a > 20
        except IndexError:
            return False

    def blit_or_fallback_rect(self, image, rect, fill_color, border_color=None, border_radius=12):
        if image:
            draw_size = fit_size(image.get_size(), rect.size)
            scaled = pygame.transform.smoothscale(image, draw_size)
            draw_rect = scaled.get_rect(center=rect.center)
            self.screen.blit(scaled, draw_rect.topleft)
        else:
            pygame.draw.rect(self.screen, fill_color, rect, border_radius=border_radius)
            if border_color:
                pygame.draw.rect(self.screen, border_color, rect, 3, border_radius=border_radius)

    def draw_settings_row(self, rect, label, active=False):
        image = self.settings_images["row_active"] if active else self.settings_images["row"]
        fill = (58, 47, 31) if active else (36, 42, 58)
        border = AMBER if active else (109, 127, 148)
        self.blit_or_fallback_rect(image, rect, fill, border, border_radius=12)
        text = self.fonts["small"].render(label, True, WHITE)
        self.screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

    def draw_fullscreen_button(self, rect):
        hovered = self.is_point_on_settings_button("fullscreen", pygame.mouse.get_pos())
        if self.fullscreen_button_images["idle"]:
            source = self.fullscreen_button_images["hover"] if hovered else self.fullscreen_button_images["idle"]
            draw_size = fit_size(source.get_size(), rect.size)
            scaled = pygame.transform.smoothscale(source, draw_size)
            draw_rect = scaled.get_rect(center=rect.center)
            self.screen.blit(scaled, draw_rect.topleft)
            text_color = (93, 49, 24) if hovered else (71, 39, 20)
            outline_color = (250, 240, 220)
            label = f"Fullscreen: {'On' if self.fullscreen else 'Off'}"
            text = self.fonts["small"].render(label, True, text_color)
            bounds = scaled.get_bounding_rect(min_alpha=20)
            text_center_x = draw_rect.x + bounds.centerx
            text_center_y = draw_rect.y + bounds.centery
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                outline = self.fonts["small"].render(label, True, outline_color)
                self.screen.blit(outline, (text_center_x - outline.get_width() // 2 + dx, text_center_y - outline.get_height() // 2 + dy))
            self.screen.blit(text, (text_center_x - text.get_width() // 2, text_center_y - text.get_height() // 2))
        else:
            self.draw_settings_row(rect, f"Fullscreen: {'On' if self.fullscreen else 'Off'}", self.fullscreen)

    def get_settings_button_surface_and_rect(self, key, hovered=False):
        rect = self.settings_buttons[key]
        image = None
        if key == "music":
            if self.music_enabled:
                image = self.settings_images["music_toggle_on_hover"] if hovered else self.settings_images["music_toggle_on"]
            else:
                image = self.settings_images["music_toggle_off_hover"] if hovered else self.settings_images["music_toggle_off"]
        elif key == "main_menu":
            image = self.button_images["hover"] if hovered else self.button_images["idle"]
        elif key == "fullscreen":
            image = self.fullscreen_button_images["hover"] if hovered else self.fullscreen_button_images["idle"]
        elif key == "difficulty_left":
            image = self.settings_images["arrow_left"]
        elif key == "difficulty_right":
            image = self.settings_images["arrow_right"]

        if not image:
            return None, rect

        draw_size = fit_size(image.get_size(), rect.size)
        scaled = pygame.transform.smoothscale(image, draw_size)
        draw_rect = scaled.get_rect(center=rect.center)
        return scaled, draw_rect

    def is_point_on_settings_button(self, key, point):
        surface, rect = self.get_settings_button_surface_and_rect(key, hovered=False)
        if surface is None:
            return self.settings_buttons[key].collidepoint(point)
        if not rect.collidepoint(point):
            return False
        local_x = point[0] - rect.x
        local_y = point[1] - rect.y
        try:
            return surface.get_at((local_x, local_y)).a > 20
        except IndexError:
            return False

    def draw_music_toggle_button(self, rect):
        hovered = self.is_point_on_settings_button("music", pygame.mouse.get_pos())
        if self.music_enabled:
            image = self.settings_images["music_toggle_on_hover"] if hovered else self.settings_images["music_toggle_on"]
        else:
            image = self.settings_images["music_toggle_off_hover"] if hovered else self.settings_images["music_toggle_off"]

        if image:
            surface, draw_rect = self.get_settings_button_surface_and_rect("music", hovered=hovered)
            self.screen.blit(surface, draw_rect.topleft)
        else:
            self.draw_settings_row(rect, f"Music: {'On' if self.music_enabled else 'Off'}", self.music_enabled)

    def draw_settings_main_menu_button(self, rect):
        hovered = self.is_point_on_settings_button("main_menu", pygame.mouse.get_pos())
        if self.button_images["idle"]:
            surface, draw_rect = self.get_settings_button_surface_and_rect("main_menu", hovered=hovered)
            self.screen.blit(surface, draw_rect.topleft)
            bounds = surface.get_bounding_rect(min_alpha=20)
            center_x = draw_rect.x + bounds.centerx
            center_y = draw_rect.y + bounds.centery - 1
            text_color = (93, 49, 24) if hovered else (71, 39, 20)
            outline_color = (250, 240, 220)
            label = "Main Menu"
            text = self.fonts["small"].render(label, True, text_color)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                outline = self.fonts["small"].render(label, True, outline_color)
                self.screen.blit(outline, (center_x - outline.get_width() // 2 + dx, center_y - outline.get_height() // 2 + dy))
            self.screen.blit(text, (center_x - text.get_width() // 2, center_y - text.get_height() // 2))
        else:
            self.draw_settings_row(rect, "Main Menu", False)

    def draw_settings_slider(self):
        slider_label = self.fonts["small"].render("Volume", True, WHITE)
        self.screen.blit(slider_label, (self.volume_slider_rect.centerx - slider_label.get_width() // 2, self.volume_slider_rect.y - 42))

        visual_rect = self.get_slider_visual_rect()
        inner_left, inner_right = self.get_slider_inner_bounds()
        slider_bar_image = crop_visible_bounds(self.settings_images["slider_bar"])
        if slider_bar_image:
            scaled_bar = pygame.transform.smoothscale(slider_bar_image, visual_rect.size)
            self.screen.blit(scaled_bar, visual_rect.topleft)
        else:
            self.blit_or_fallback_rect(None, visual_rect, (38, 47, 65), None, border_radius=8)

        knob_x = int(inner_left + (inner_right - inner_left) * self.volume)
        visual_fill_width = max(8, knob_x - visual_rect.left)
        fill_rect = pygame.Rect(visual_rect.left, visual_rect.y, visual_fill_width, visual_rect.height)
        slider_fill_image = crop_visible_bounds(self.settings_images["slider_fill"])
        if slider_fill_image:
            full_fill = pygame.transform.smoothscale(slider_fill_image, visual_rect.size)
            visible_fill = full_fill.subsurface((0, 0, visual_fill_width, visual_rect.height))
            self.screen.blit(visible_fill, fill_rect.topleft)
        else:
            pygame.draw.rect(self.screen, AMBER if self.music_enabled else (110, 110, 110), fill_rect, border_radius=8)

        slider_knob_image = crop_visible_bounds(self.settings_images["slider_knob"])
        if slider_knob_image:
            knob_size = fit_size(slider_knob_image.get_size(), (34, 34))
            scaled_knob = pygame.transform.smoothscale(slider_knob_image, knob_size)
            knob_rect = pygame.Rect(0, 0, knob_size[0], knob_size[1])
            knob_rect.center = (knob_x, self.volume_slider_rect.centery)
            self.screen.blit(scaled_knob, knob_rect.topleft)
        else:
            pygame.draw.circle(self.screen, WHITE if self.music_enabled else (170, 170, 170), (knob_x, self.volume_slider_rect.centery), 14)

    # --- MENU BUTTONS ---
    def build_menu_buttons(self):
        labels = [("play", "Play"), ("continue", "Continue"), ("settings", "Settings"), ("exit", "Exit")]
        area = pygame.Rect(655, 95, 450, 550)
        self.menu_buttons = self.build_vertical_button_layout(labels, area)
        return self.menu_buttons

    def build_pause_buttons(self):
        labels = [("continue", "Continue"), ("settings", "Settings"), ("main_menu", "Main Menu")]
        area = pygame.Rect(WIDTH // 2 - 230, 240, 460, 320)
        self.pause_buttons = self.build_vertical_button_layout(labels, area)
        return self.pause_buttons

    def get_button_collection(self, state):
        return self.pause_buttons if state == "paused" else self.menu_buttons

    def draw_menu_button(self, key, mouse_pos, state="menu"):
        buttons = self.get_button_collection(state)
        button = buttons[key]
        rect = button["rect"]
        hovered = self.is_point_on_button_texture(key, mouse_pos, state)
        if self.button_images["idle"]:
            scaled, draw_rect = self.get_button_surface_and_rect(key, hovered, state)
            self.screen.blit(scaled, draw_rect.topleft)
            bounds = scaled.get_bounding_rect(min_alpha=20)
            center_x = rect.x + bounds.centerx
            center_y = rect.y + bounds.centery - 1
            text_color = (93, 49, 24) if hovered else (71, 39, 20)
            outline_color = (250, 240, 220)
            text = self.fonts["small"].render(button["label"], True, text_color)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                outline = self.fonts["small"].render(button["label"], True, outline_color)
                self.screen.blit(outline, (center_x - outline.get_width() // 2 + dx, center_y - outline.get_height() // 2 + dy))
            self.screen.blit(text, (center_x - text.get_width() // 2, center_y - text.get_height() // 2))
        else:
            text_color = BLACK if hovered else WHITE
            shadow = rect.move(0, 5)
            image_path = self.asset_paths["button_hover"] if hovered else self.asset_paths["button"]
            button_image = load_scaled_image(image_path, rect.size)
            if button_image:
                pygame.draw.rect(self.screen, (9, 11, 17), shadow, border_radius=16)
                self.screen.blit(button_image, rect.topleft)
            else:
                fill = (245, 209, 102) if hovered else (28, 35, 48)
                border = (255, 241, 188) if hovered else (92, 114, 138)
                pygame.draw.rect(self.screen, (9, 11, 17), shadow, border_radius=16)
                pygame.draw.rect(self.screen, fill, rect, border_radius=16)
                pygame.draw.rect(self.screen, border, rect, 3, border_radius=16)
            label = self.fonts["small"].render(button["label"], True, text_color)
            self.screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

    def draw_menu_logo(self):
        logo = self.ui_images["menu_logo"]
        if not logo:
            return
        area = pygame.Rect(62, 42, 540, 220)
        draw_size = fit_size(logo.get_size(), area.size)
        scaled = pygame.transform.smoothscale(logo, draw_size)
        draw_rect = scaled.get_rect(center=area.center)
        self.screen.blit(scaled, draw_rect.topleft)

    # --- MAIN MENU ---
    def draw_menu(self):
        if self.ui_images["menu_background"]:
            self.screen.blit(self.ui_images["menu_background"], (0, 0))
        else:
            draw_forest_background(self.screen, 0)
        self.draw_menu_logo()
        mouse_pos = pygame.mouse.get_pos()
        self.build_menu_buttons()
        for key in ("play", "continue", "settings", "exit"):
            self.draw_menu_button(key, mouse_pos)

    def draw_pause_menu(self):
        self.current_level.draw(self.screen, self.fonts, self.level_backgrounds)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 178))
        self.screen.blit(overlay, (0, 0))

        card = pygame.Rect(WIDTH // 2 - 240, 118, 480, 138)
        draw_note_panel(self.screen, card, pin_color=(156, 54, 44), alpha=222)
        title = self.fonts["title"].render("Paused", True, (82, 50, 30))
        subtitle = self.fonts["small"].render("Esc to continue", True, (102, 72, 46))
        self.screen.blit(title, (card.centerx - title.get_width() // 2, card.y + 20))
        self.screen.blit(subtitle, (card.centerx - subtitle.get_width() // 2, card.y + 78))

        mouse_pos = pygame.mouse.get_pos()
        self.build_pause_buttons()
        for key in ("continue", "settings", "main_menu"):
            self.draw_menu_button(key, mouse_pos, state="paused")

    # --- SETTINGS ---
    def draw_settings(self):
        if self.ui_images["settings_background"]:
            self.screen.blit(self.ui_images["settings_background"], (0, 0))
        else:
            draw_bunker_background(self.screen, 0, False)

        self.draw_settings_slider()

        music_rect = self.settings_buttons["music"]
        fullscreen_rect = self.settings_buttons["fullscreen"]
        diff_left = self.settings_buttons["difficulty_left"]
        diff_value = self.settings_buttons["difficulty_value"]
        diff_right = self.settings_buttons["difficulty_right"]

        self.draw_music_toggle_button(music_rect)
        self.draw_fullscreen_button(fullscreen_rect)
        self.draw_settings_main_menu_button(self.settings_buttons["main_menu"])

        self.blit_or_fallback_rect(self.settings_images["difficulty"], diff_value, (36, 42, 58), (109, 127, 148), border_radius=12)
        diff_text = self.fonts["small"].render(f"Difficulty: {self.difficulty_options[self.difficulty_index]}", True, WHITE)
        self.screen.blit(diff_text, (diff_value.centerx - diff_text.get_width() // 2, diff_value.centery - diff_text.get_height() // 2))

        if self.settings_images["arrow_left"]:
            left_image = scale_to_rect(self.settings_images["arrow_left"], diff_left.size)
            self.screen.blit(left_image, diff_left.topleft)
        else:
            self.blit_or_fallback_rect(None, diff_left, (36, 42, 58), (109, 127, 148), border_radius=12)
            left_text = self.fonts["small"].render("<", True, WHITE)
            self.screen.blit(left_text, (diff_left.centerx - left_text.get_width() // 2, diff_left.centery - left_text.get_height() // 2))

        if self.settings_images["arrow_right"]:
            right_image = scale_to_rect(self.settings_images["arrow_right"], diff_right.size)
            self.screen.blit(right_image, diff_right.topleft)
        else:
            self.blit_or_fallback_rect(None, diff_right, (36, 42, 58), (109, 127, 148), border_radius=12)
            right_text = self.fonts["small"].render(">", True, WHITE)
            self.screen.blit(right_text, (diff_right.centerx - right_text.get_width() // 2, diff_right.centery - right_text.get_height() // 2))

    def handle_menu_click(self, mouse_pos, state="menu"):
        buttons = self.get_button_collection(state)
        if not buttons:
            if state == "paused":
                buttons = self.build_pause_buttons()
            else:
                buttons = self.build_menu_buttons()
        for key in buttons:
            if self.is_point_on_button_texture(key, mouse_pos, state):
                play_sfx("menu")
                if state == "paused":
                    if key == "continue":
                        self.state = "playing"
                    elif key == "settings":
                        self.settings_return_state = "paused"
                        self.state = "settings"
                    elif key == "main_menu":
                        self.state = "menu"
                    break
                if key == "continue":
                    self.continue_game()
                elif key == "play":
                    self.start_new_game()
                elif key == "settings":
                    self.settings_return_state = "menu"
                    self.state = "settings"
                elif key == "exit":
                    return False
                break
        return True

    def handle_settings_mouse_down(self, mouse_pos):
        hitbox = self.get_slider_visual_rect().inflate(0, 24)
        inner_left, inner_right = self.get_slider_inner_bounds()
        knob_x = int(inner_left + (inner_right - inner_left) * self.volume)
        knob_rect = pygame.Rect(knob_x - 16, self.volume_slider_rect.centery - 16, 32, 32)
        if hitbox.collidepoint(mouse_pos) or knob_rect.collidepoint(mouse_pos):
            self.dragging_volume = True
            self.set_volume_from_pos(mouse_pos[0])
            return
        if self.is_point_on_settings_button("music", mouse_pos):
            self.toggle_music()
            return
        if self.is_point_on_settings_button("fullscreen", mouse_pos):
            self.toggle_fullscreen()
            return
        if self.is_point_on_settings_button("main_menu", mouse_pos):
            self.dragging_volume = False
            play_sfx("menu")
            self.state = "menu"
            self.settings_return_state = "menu"
            return
        if self.is_point_on_settings_button("difficulty_left", mouse_pos):
            play_sfx("menu")
            self.difficulty_index = (self.difficulty_index - 1) % len(self.difficulty_options)
            self.restart_all()
            self.state = "settings"
            return
        if self.is_point_on_settings_button("difficulty_right", mouse_pos):
            play_sfx("menu")
            self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_options)
            self.restart_all()
            self.state = "settings"

    def handle_settings_mouse_up(self):
        self.dragging_volume = False

    def draw_end(self, victory):
        draw_boss_background(self.screen, 0.25 if victory else 0.1)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 180))
        self.screen.blit(overlay, (0, 0))
        if victory and self.true_ending:
            heading = "True ending: the bunker is sealed for good."
        else:
            heading = "The diary is decoded. The twins escape." if victory else "The bunker wins this round."
        panel = pygame.Rect(WIDTH // 2 - 420, 150, 840, 360)
        draw_note_panel(self.screen, panel, pin_color=(152, 52, 42), alpha=226)
        accent = (154, 104, 44) if victory else (126, 38, 32)
        title = self.fonts["title"].render(heading, True, accent)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 30))

        badge = pygame.Rect(panel.centerx - 92, panel.y + 92, 184, 34)
        draw_note_panel(self.screen, badge, pin_color=(168, 62, 46), alpha=210)
        badge_text = "Victory" if victory else "Defeat"
        badge_color = (112, 76, 36) if victory else (108, 42, 34)
        badge_render = self.fonts["body"].render(badge_text, True, badge_color)
        self.screen.blit(badge_render, (badge.centerx - badge_render.get_width() // 2, badge.y + 5))

        icon_rect = pygame.Rect(panel.x + 48, panel.y + 56, 112, 148)
        if victory:
            draw_portal(self.screen, icon_rect.inflate(-18, -10), 0.92 if self.true_ending else 0.72)
        else:
            draw_rift(self.screen, icon_rect.inflate(-20, -8), 1.6)

        lines = ["Press R to restart the whole adventure.", "Press Esc to close the game."]
        if victory:
            if self.true_ending:
                lines.insert(0, "All three bunker ciphers were solved. The diary reveals how to seal the tear behind them.")
                lines.insert(1, "Stan stabilizes the portal, Dipper locks the breach, and Bill's shadow cannot return.")
            else:
                lines.insert(0, "Stan opens the tear, the portal stabilizes, and Bill's shadow fades.")
        body_color = (88, 60, 40)
        text_left = panel.x + 186
        text_top = panel.y + 146
        text_width = panel.width - 236
        text_y = text_top
        line_gap = 12
        paragraph_gap = 18
        for idx, paragraph in enumerate(lines):
            wrapped = render_wrapped_lines(self.fonts["body"], paragraph, body_color, text_width)
            for rendered in wrapped:
                self.screen.blit(rendered, (text_left, text_y))
                text_y += rendered.get_height() + line_gap
            if idx < len(lines) - 1:
                text_y += paragraph_gap

    def open_cipher_puzzle(self, cipher_id):
        if not isinstance(self.current_level, BunkerLevel):
            return
        cipher = next((item for item in self.current_level.ciphers if item["id"] == cipher_id), None)
        if not cipher or cipher["solved"]:
            return
        puzzle = self.current_level.cipher_puzzles[cipher_id]
        self.current_level.reset_cipher_puzzle(cipher_id)
        if puzzle["type"] == "timed_seals":
            puzzle["timer"] = puzzle["duration"]
        self.active_cipher_id = cipher_id
        self.cipher_modal_message = "Solve the cipher. Esc closes the puzzle."
        self.cipher_modal_message_timer = 0.0
        self.state = "cipher_puzzle"
        play_sfx("cipher_open")

    def close_cipher_puzzle(self):
        if isinstance(self.current_level, BunkerLevel):
            self.current_level.player.invuln = max(self.current_level.player.invuln, 2.0)
        self.active_cipher_id = None
        self.cipher_modal_message = ""
        self.cipher_modal_message_timer = 0.0
        self.state = "playing"

    def get_cipher_modal_nodes(self, cipher_id, panel):
        if cipher_id == "glow":
            size = 52
            gap = 44
            start_x = panel.centerx - (size * 3 + gap * 2) // 2
            y = panel.y + 158
            return [pygame.Rect(start_x + index * (size + gap), y, size, size) for index in range(3)]
        if cipher_id == "stairs":
            width, height = 118, 28
            return [
                pygame.Rect(panel.x + 86, panel.bottom - 132, width, height),
                pygame.Rect(panel.centerx - width // 2, panel.bottom - 192, width, height),
                pygame.Rect(panel.right - 86 - width, panel.bottom - 252, width, height),
            ]
        size = 58
        return [
            pygame.Rect(panel.centerx - size // 2, panel.y + 138, size, size),
            pygame.Rect(panel.x + 126, panel.bottom - 164, size, size),
            pygame.Rect(panel.right - 126 - size, panel.bottom - 164, size, size),
        ]

    def update_cipher_puzzle(self, dt):
        if self.cipher_modal_message_timer > 0:
            self.cipher_modal_message_timer = max(0.0, self.cipher_modal_message_timer - dt)
        if not isinstance(self.current_level, BunkerLevel) or not self.active_cipher_id:
            return
        puzzle = self.current_level.cipher_puzzles[self.active_cipher_id]
        if puzzle["type"] == "timed_seals" and not any(cipher["id"] == self.active_cipher_id and cipher["solved"] for cipher in self.current_level.ciphers):
            puzzle["timer"] = max(0.0, puzzle["timer"] - dt)
            if puzzle["timer"] <= 0:
                self.current_level.reset_cipher_puzzle(self.active_cipher_id)
                puzzle["timer"] = puzzle["duration"]
                self.cipher_modal_message = "The seals collapsed. Try again."
                self.cipher_modal_message_timer = 1.8

    def handle_cipher_puzzle_click(self, mouse_pos):
        if not isinstance(self.current_level, BunkerLevel) or not self.active_cipher_id:
            return
        cipher = next(item for item in self.current_level.ciphers if item["id"] == self.active_cipher_id)
        puzzle = self.current_level.cipher_puzzles[self.active_cipher_id]
        panel = pygame.Rect(WIDTH // 2 - 330, HEIGHT // 2 - 220, 660, 440)
        node_rects = self.get_cipher_modal_nodes(self.active_cipher_id, panel)
        clicked_index = next((index for index, rect in enumerate(node_rects) if rect.collidepoint(mouse_pos)), None)
        if clicked_index is None:
            return

        if puzzle["type"] in ("sequence", "plates"):
            if clicked_index == puzzle["progress"]:
                puzzle["nodes"][clicked_index]["active"] = True
                puzzle["progress"] += 1
                self.cipher_modal_message = "Correct."
                self.cipher_modal_message_timer = 0.7
                if puzzle["progress"] >= len(puzzle["nodes"]):
                    self.current_level.solve_cipher(self.active_cipher_id)
                    self.close_cipher_puzzle()
            else:
                self.current_level.reset_cipher_puzzle(self.active_cipher_id)
                self.cipher_modal_message = "Wrong order. Reset."
                self.cipher_modal_message_timer = 1.1
        elif puzzle["type"] == "timed_seals":
            if not puzzle["nodes"][clicked_index]["active"]:
                puzzle["nodes"][clicked_index]["active"] = True
                self.cipher_modal_message = "Seal locked."
                self.cipher_modal_message_timer = 0.7
                if all(node["active"] for node in puzzle["nodes"]):
                    self.current_level.solve_cipher(self.active_cipher_id)
                    self.close_cipher_puzzle()

    def draw_cipher_puzzle(self):
        if not isinstance(self.current_level, BunkerLevel) or not self.active_cipher_id:
            return
        cipher = next(item for item in self.current_level.ciphers if item["id"] == self.active_cipher_id)
        puzzle = self.current_level.cipher_puzzles[self.active_cipher_id]
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 192))
        self.screen.blit(overlay, (0, 0))
        panel = pygame.Rect(WIDTH // 2 - 330, HEIGHT // 2 - 220, 660, 440)
        cipher_bg = self.ui_images.get("cipher_background")
        if cipher_bg:
            scaled = pygame.transform.smoothscale(cipher_bg, panel.size)
            self.screen.blit(scaled, panel.topleft)
        else:
            pygame.draw.rect(self.screen, (20, 24, 34), panel, border_radius=22)
            pygame.draw.rect(self.screen, (182, 200, 214), panel, 3, border_radius=22)

        text_left = panel.x + 42
        text_right = panel.right - 42
        text_width = text_right - text_left
        title_font = load_font(self.asset_paths["font_title"], 28, "georgia", bold=True)
        hint_font = load_font(self.asset_paths["font_ui"], 21, "georgia", bold=True)
        reward_font = load_font(self.asset_paths["font_mono"], 15, "consolas")
        footer_font = load_font(self.asset_paths["font_mono"], 14, "consolas")

        title_color = (245, 241, 232)
        hint_color = (247, 243, 228)
        reward_color = (223, 186, 106)
        shadow_color = (34, 22, 18)

        def blit_center_text(rendered, center_x, y, shadow_offset=2):
            shadow = rendered.copy()
            shadow.fill(shadow_color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
            shadow.set_alpha(210)
            self.screen.blit(shadow, (center_x - shadow.get_width() // 2 + shadow_offset, y + shadow_offset))
            self.screen.blit(rendered, (center_x - rendered.get_width() // 2, y))

        title = title_font.render(cipher["title"], True, title_color)
        blit_center_text(title, panel.centerx, panel.y + 22)

        hint_lines = render_wrapped_lines(hint_font, cipher["hint"], hint_color, text_width - 28)
        reward_text = cipher["reward"].replace("Reward:", "Reward")
        reward_lines = render_wrapped_lines(reward_font, reward_text, reward_color, text_width - 90)

        text_y = panel.y + 86
        for line in hint_lines:
            blit_center_text(line, panel.centerx, text_y, shadow_offset=1)
            text_y += line.get_height() + 6

        reward_y = min(text_y + 8, panel.y + 140)
        reward_chip = pygame.Rect(panel.x + 86, reward_y - 4, panel.width - 172, 32)
        chip = pygame.Surface(reward_chip.size, pygame.SRCALPHA)
        pygame.draw.rect(chip, (28, 18, 14, 112), chip.get_rect(), border_radius=14)
        pygame.draw.rect(chip, (180, 132, 78, 120), chip.get_rect(), 1, border_radius=14)
        self.screen.blit(chip, reward_chip.topleft)
        reward_line = reward_lines[0] if reward_lines else reward_font.render(reward_text, True, reward_color)
        blit_center_text(reward_line, reward_chip.centerx, reward_chip.y + 7, shadow_offset=1)

        node_rects = self.get_cipher_modal_nodes(self.active_cipher_id, panel)
        if puzzle["type"] == "sequence":
            for index, rect in enumerate(node_rects):
                draw_cipher_lamp(self.screen, rect, puzzle["nodes"][index]["active"], index + 1)
        elif puzzle["type"] == "plates":
            for index, rect in enumerate(node_rects):
                draw_cipher_plate(self.screen, rect, puzzle["nodes"][index]["active"], index + 1)
            helper = self.fonts["tiny"].render("Click the plates from the lowest stair to the highest.", True, CYAN)
            self.screen.blit(helper, (panel.centerx - helper.get_width() // 2, panel.bottom - 94))
        elif puzzle["type"] == "timed_seals":
            for index, rect in enumerate(node_rects):
                draw_cipher_seal(self.screen, rect, puzzle["nodes"][index]["active"], index + 1)
            timer = hint_font.render(f"Seal timer: {puzzle['timer']:.1f}s", True, CYAN)
            helper = footer_font.render("Seal all three tears before the timer resets.", True, CYAN)
            blit_center_text(timer, panel.centerx, panel.bottom - 140, shadow_offset=1)
            blit_center_text(helper, panel.centerx, panel.bottom - 108, shadow_offset=1)

        if self.cipher_modal_message:
            color = AMBER if "Correct" in self.cipher_modal_message or "locked" in self.cipher_modal_message.lower() else CRIMSON if "Wrong" in self.cipher_modal_message or "collapsed" in self.cipher_modal_message.lower() else WHITE
            message = hint_font.render(self.cipher_modal_message, True, color)
            blit_center_text(message, panel.centerx, panel.bottom - 66, shadow_offset=1)

        close_hint = footer_font.render("Esc to return to the bunker", True, MIST)
        blit_center_text(close_hint, panel.centerx, panel.bottom - 34, shadow_offset=1)

    def draw_film_overlay(self):
        tick = pygame.time.get_ticks()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        flicker_alpha = 10 + int(8 * (0.5 + 0.5 * math.sin(tick * 0.018)))
        overlay.fill((28, 22, 14, flicker_alpha))

        for y in range(0, HEIGHT, 4):
            alpha = 8 if (y // 4 + tick // 45) % 2 == 0 else 4
            pygame.draw.line(overlay, (42, 32, 20, alpha), (0, y), (WIDTH, y))

        random.seed(tick // 40)
        for _ in range(140):
            x = random.randrange(WIDTH)
            y = random.randrange(HEIGHT)
            alpha = random.randint(10, 28)
            color = random.randint(150, 235)
            overlay.set_at((x, y), (color, color, color, alpha))

        for _ in range(3):
            scratch_x = random.randint(20, WIDTH - 20)
            scratch_h = random.randint(HEIGHT // 3, HEIGHT - 40)
            scratch_y = random.randint(0, HEIGHT - scratch_h)
            pygame.draw.line(overlay, (248, 239, 210, 34), (scratch_x, scratch_y), (scratch_x, scratch_y + scratch_h), 1)
        self.screen.blit(overlay, (0, 0))

    def handle_result(self, result):
        if result == "next":
            if isinstance(self.current_level, BunkerLevel):
                self.bunker_bonuses = self.current_level.get_completed_cipher_ids()
            self.level_index += 1
            if self.level_index >= len(self.levels):
                self.clear_progress()
                self.state = "victory"
            else:
                if isinstance(self.levels[self.level_index], BossLevel):
                    self.levels[self.level_index].apply_bunker_bonuses(self.bunker_bonuses)
                self.save_progress()
                self.banner_timer = 3.0
                self.overlay_text = f"Level {self.level_index + 1}"
        elif result == "lose":
            self.start_death_restart()
        elif result == "win":
            if isinstance(self.current_level, BossLevel):
                self.true_ending = self.current_level.true_escape
            self.clear_progress()
            self.state = "victory"

    def draw_banner(self):
        if self.banner_timer <= 0:
            return
        alpha = int(255 * min(1.0, self.banner_timer))
        text = self.overlay_text or f"Level {self.level_index + 1}"
        card = pygame.Surface((420, 88), pygame.SRCALPHA)
        draw_note_panel(card, card.get_rect(), pin_color=(152, 52, 42), alpha=min(220, alpha))
        self.screen.blit(card, (WIDTH // 2 - 210, 118))
        banner = self.fonts["title"].render(text, True, (84, 52, 32))
        banner.set_alpha(alpha)
        self.screen.blit(banner, (WIDTH // 2 - banner.get_width() // 2, 138))

    # --- MAIN LOOP ---
    def run(self):
        self.overlay_text = "Level 1"
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
            self.update_mouse_lock()
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "menu":
                        running = self.handle_menu_click(event.pos)
                    elif self.state == "paused":
                        self.handle_settings_mouse_up()
                        running = self.handle_menu_click(event.pos, state="paused")
                    elif self.state == "settings":
                        self.handle_settings_mouse_down(event.pos)
                    elif self.state == "cipher_puzzle":
                        self.handle_cipher_puzzle_click(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.state == "settings":
                        self.handle_settings_mouse_up()
                elif event.type == pygame.MOUSEMOTION:
                    if self.state == "settings" and self.dragging_volume:
                        self.set_volume_from_pos(event.pos[0])
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "settings":
                            self.dragging_volume = False
                            self.state = self.settings_return_state
                        elif self.state == "cipher_puzzle":
                            self.close_cipher_puzzle()
                        elif self.state in ("playing", "paused"):
                            self.toggle_pause()
                        elif self.state == "menu":
                            running = False
                        else:
                            running = False
                    elif self.state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "playing"
                    elif self.state in ("game_over", "victory") and event.key == pygame.K_r:
                        self.restart_all()
            if self.state == "menu":
                self.draw_menu()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "paused":
                self.draw_pause_menu()
            elif self.state == "playing":
                self.banner_timer = max(0.0, self.banner_timer - dt)
                result = self.current_level.update(dt, keys)
                self.current_level.draw(self.screen, self.fonts, self.level_backgrounds)
                self.draw_banner()
                if isinstance(result, tuple) and result[0] == "cipher":
                    self.open_cipher_puzzle(result[1])
                elif result:
                    self.handle_result(result)
            elif self.state == "cipher_puzzle":
                self.current_level.draw(self.screen, self.fonts, self.level_backgrounds)
                self.update_cipher_puzzle(dt)
                self.draw_cipher_puzzle()
            elif self.state == "death_notice":
                self.current_level.draw(self.screen, self.fonts, self.level_backgrounds)
                self.draw_death_notice()
                self.death_timer = max(0.0, self.death_timer - dt)
                if self.death_timer <= 0:
                    self.finish_death_restart()
            elif self.state == "game_over":
                self.draw_end(False)
            elif self.state == "victory":
                self.draw_end(True)
            self.draw_film_overlay()
            pygame.display.flip()
            self.force_center_mouse()
        if hasattr(pygame.mouse, "set_relative_mode"):
            try:
                pygame.mouse.set_relative_mode(False)
            except pygame.error:
                pass
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        pygame.quit()


if __name__ == "__main__":
    Game().run()

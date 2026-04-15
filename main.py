import math
import os
import random
import struct
import tempfile
import wave
import json
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

PARALLAX_IMAGE_CACHE = {}

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
SAVE_FILE = os.path.join(BASE_DIR, "savegame.json")


def clamp(value, low, high):
    return max(low, min(high, value))


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


def draw_flashlight_beam(surface, origin, facing, active=True):
    if not active:
        return
    tick = pygame.time.get_ticks()
    flicker = 0.96 + 0.04 * math.sin(tick * 0.01)
    beam_w = 210
    beam_h = 132
    beam = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)

    outer = [(10, beam_h // 2), (102, 22), (beam_w - 12, 38), (beam_w - 12, beam_h - 38), (102, beam_h - 22)]
    mid = [(14, beam_h // 2), (92, 36), (beam_w - 34, 48), (beam_w - 34, beam_h - 48), (92, beam_h - 36)]
    core = [(18, beam_h // 2), (78, 47), (beam_w - 70, 56), (beam_w - 70, beam_h - 56), (78, beam_h - 47)]

    pygame.draw.polygon(beam, (255, 232, 178, int(22 * flicker)), outer)
    pygame.draw.polygon(beam, (255, 238, 196, int(30 * flicker)), mid)
    pygame.draw.polygon(beam, (255, 244, 218, int(18 * flicker)), core)

    fog = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
    for index in range(5):
        glow_w = 44 + index * 26
        glow_h = 24 + index * 12
        glow_x = beam_w - 70 - index * 24
        glow_y = beam_h // 2 - glow_h // 2
        pygame.draw.ellipse(fog, (255, 242, 212, max(4, 14 - index * 2)), (glow_x, glow_y, glow_w, glow_h))
    beam.blit(fog, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    dust = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
    for index in range(5):
        px = 70 + index * 24 + int(5 * math.sin(tick * 0.002 + index))
        py = 30 + (index * 17) % (beam_h - 60)
        radius = 1 + (index % 2)
        pygame.draw.circle(dust, (255, 245, 225, 10), (px, py), radius)
    beam.blit(dust, (0, 0))

    if facing < 0:
        beam = pygame.transform.flip(beam, True, False)

    beam_rect = beam.get_rect()
    beam_rect.midleft = (origin[0] - 8, origin[1]) if facing > 0 else (origin[0] + 8, origin[1])
    surface.blit(beam, beam_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)

    glow = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 223, 150, int(34 * flicker)), (24, 24), 12)
    pygame.draw.circle(glow, (255, 243, 214, int(46 * flicker)), (24, 24), 5)
    glow_rect = glow.get_rect(center=origin)
    surface.blit(glow, glow_rect.topleft, special_flags=pygame.BLEND_RGBA_ADD)


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
        self.speed = 370
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
            frame_index = int(self.run_anim_time * 10) % len(run_sprites)
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
        "skin": (240, 214, 186),
        "nose": (224, 176, 144),
        "beard": (245, 244, 236),
        "beard_shade": (205, 212, 214),
        "tunic": (92, 118, 84),
        "tunic_light": (120, 150, 110),
        "belt": (96, 61, 32),
        "boot": (64, 48, 42),
        "hat": (170, 34, 36),
        "hat_light": (212, 68, 72),
        "gold": (233, 193, 94),
        "outline": (36, 28, 24),
        "lantern": (244, 213, 120),
        "glow": (255, 224, 146, 72),
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
        width, height = 72, 64
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        base_y = 10 + bob

        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, colors["glow"], (15, 15), 15)
        surface.blit(glow, (40, base_y + 18))
        pygame.draw.ellipse(surface, (0, 0, 0, 55), (17, 54 + bob, 38, 8))

        pygame.draw.polygon(surface, colors["hat"], [(18, base_y + 12), (31, base_y - 2), (43, base_y + 11), (38, base_y + 16), (23, base_y + 16)])
        pygame.draw.rect(surface, colors["hat"], (17, base_y + 13, 27, 6), border_radius=3)
        pygame.draw.rect(surface, colors["hat_light"], (23, base_y + 4, 6, 9), border_radius=2)
        pygame.draw.circle(surface, colors["gold"], (39, base_y + 8), 3)

        pygame.draw.circle(surface, colors["skin"], (30, base_y + 22), 10)
        pygame.draw.circle(surface, colors["nose"], (35, base_y + 24), 3)
        eye_y = base_y + 21
        if blink:
            pygame.draw.line(surface, colors["eye"], (26, eye_y), (29, eye_y), 2)
        else:
            pygame.draw.circle(surface, colors["eye"], (27, eye_y), 2)
        pygame.draw.circle(surface, colors["eye"], (32, eye_y + 1), 1)

        pygame.draw.polygon(surface, colors["beard"], [(20, base_y + 25), (40, base_y + 25), (45, base_y + 42), (30, base_y + 52), (15, base_y + 42)])
        pygame.draw.line(surface, colors["beard_shade"], (30, base_y + 27), (30, base_y + 49), 2)
        pygame.draw.line(surface, colors["beard_shade"], (25, base_y + 31), (22, base_y + 43), 2)
        pygame.draw.line(surface, colors["beard_shade"], (35, base_y + 31), (38, base_y + 43), 2)

        pygame.draw.rect(surface, colors["tunic"], (18, base_y + 31, 24, 17), border_radius=6)
        pygame.draw.rect(surface, colors["tunic_light"], (22, base_y + 34, 16, 6), border_radius=3)
        pygame.draw.rect(surface, colors["belt"], (19, base_y + 41, 22, 4), border_radius=2)
        pygame.draw.rect(surface, colors["gold"], (28, base_y + 40, 5, 6), border_radius=2)

        arm_y = base_y + 34 + (1 if step in (1, 2) else 0)
        pygame.draw.line(surface, colors["skin"], (40, base_y + 35), (48, arm_y + 3), 4)
        pygame.draw.line(surface, colors["outline"], (49, arm_y + 5), (49, arm_y + 13), 2)
        pygame.draw.rect(surface, (86, 68, 44), (44, arm_y + 10, 10, 12), border_radius=2)
        pygame.draw.rect(surface, colors["lantern"], (46, arm_y + 12, 6, 6), border_radius=2)

        arm_offset = -2 if step in (0, 3) else 2
        pygame.draw.line(surface, colors["tunic_light"], (19, base_y + 35), (13, base_y + 38 + arm_offset), 4)

        leg_specs = [(-4, 4), (4, -4), (2, -2), (-2, 2)]
        left_dx, right_dx = leg_specs[step % len(leg_specs)]
        hip_y = base_y + 46
        pygame.draw.line(surface, colors["boot"], (26, hip_y), (24 + left_dx, base_y + 57), 5)
        pygame.draw.line(surface, colors["boot"], (34, hip_y), (36 + right_dx, base_y + 57), 5)
        pygame.draw.line(surface, colors["boot"], (20 + left_dx, base_y + 58), (28 + left_dx, base_y + 58), 4)
        pygame.draw.line(surface, colors["boot"], (32 + right_dx, base_y + 58), (40 + right_dx, base_y + 58), 4)

        pygame.draw.lines(surface, colors["outline"], False, [(21, base_y + 16), (18, base_y + 13), (31, base_y - 1), (42, base_y + 11)], 1)
        pygame.draw.arc(surface, colors["outline"], (18, base_y + 12, 24, 20), math.pi, math.tau, 1)
        pygame.draw.line(surface, colors["outline"], (20, base_y + 25), (16, base_y + 42), 1)
        pygame.draw.line(surface, colors["outline"], (40, base_y + 25), (44, base_y + 42), 1)
        pygame.draw.line(surface, colors["outline"], (23, base_y + 31), (23, base_y + 44), 1)
        pygame.draw.line(surface, colors["outline"], (37, base_y + 31), (37, base_y + 44), 1)
        return trim_transparent_bounds(surface)

    @classmethod
    def draw(cls, surface, rect, anim_time=0.0):
        sprite_pack = cls.sprites
        run_sprites = sprite_pack["run"]
        sprite = sprite_pack["idle"]
        if run_sprites:
            frame_index = int(anim_time * 11) % len(run_sprites)
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
        player.reveal_active = keys[pygame.K_f] and player.reveal_energy > 0.2
        screen_x = player.rect.x - self.camera_x

        if moving:
            self.world_speed = 320
            player.facing = 1
            if screen_x < 330:
                player.rect.x += int(260 * dt)
            else:
                self.progress += 270 * dt
        elif retreat:
            self.world_speed = 120
            player.facing = -1
            if screen_x > 140:
                player.rect.x -= int(240 * dt)
            else:
                self.progress = max(0.0, self.progress - 100 * dt)
        else:
            self.world_speed = 0

        player.rect.x = clamp(player.rect.x, 40, self.length + 220)
        self.camera_x = clamp(self.progress, 0, self.length)

        if player.on_ground and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]):
            player.vel.y = player.jump_strength
            player.on_ground = False

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
        self.length = 2600
        self.reset()

    def reset(self):
        self.player = Player()
        self.player.reset_position(80, 420)
        self.player.health = 5
        self.camera_x = 0
        self.gravity = 1650
        self.current_gravity = 1
        self.collected = 0
        self.target_pages = 5
        self.done = False
        self.message = "Level 2: Use the diary lens to reveal hidden paths, dodge traps, solve ciphers."
        self.particles = []
        self.platforms = [
            pygame.Rect(0, 520, 420, 200),
            pygame.Rect(470, 480, 180, 24),
            pygame.Rect(780, 440, 180, 24),
            pygame.Rect(1070, 390, 170, 24),
            pygame.Rect(1370, 330, 180, 24),
            pygame.Rect(1620, 480, 320, 24),
            pygame.Rect(1970, 420, 170, 24),
            pygame.Rect(2250, 350, 220, 24),
        ]
        self.hidden_platforms = [
            pygame.Rect(610, 365, 120, 20),
            pygame.Rect(1235, 255, 110, 20),
            pygame.Rect(1760, 370, 120, 20),
        ]
        self.gravity_zones = [
            pygame.Rect(1160, 88, 250, 188),
            pygame.Rect(2140, 96, 120, 168),
        ]
        self.moving_platforms = [{
            "rect": pygame.Rect(1470, 250, 150, 22),
            "start": pygame.Vector2(1470, 250),
            "end": pygame.Vector2(1720, 170),
            "time": 0.0,
        }]
        self.spikes = [
            pygame.Rect(515, 504, 90, 16),
            pygame.Rect(850, 424, 76, 16),
            pygame.Rect(1705, 464, 108, 16),
            pygame.Rect(2310, 334, 92, 16),
        ]
        self.ciphers = [
            {"rect": pygame.Rect(845, 388, 54, 52), "solved": False, "hint": "Cipher: TRUST NO GLOW"},
            {"rect": pygame.Rect(1840, 448, 54, 52), "solved": False, "hint": "Cipher: LIGHT SHOWS STAIRS"},
        ]
        self.pages = [
            {"rect": pygame.Rect(1095, 338, 26, 32), "hidden": False, "taken": False},
            {"rect": pygame.Rect(1275, 205, 26, 32), "hidden": True, "taken": False},
            {"rect": pygame.Rect(1705, 445, 26, 32), "hidden": False, "taken": False},
            {"rect": pygame.Rect(1795, 320, 26, 32), "hidden": True, "taken": False},
            {"rect": pygame.Rect(2365, 300, 26, 32), "hidden": False, "taken": False},
        ]

    def active_platforms(self):
        return list(self.platforms) + [item["rect"] for item in self.moving_platforms]

    def update(self, dt, keys):
        player = self.player
        player.update_common(dt)
        player.reveal_active = keys[pygame.K_f] and player.reveal_energy > 0.25

        # Player movement for level 2, including gravity flips and platform collisions.
        in_reverse_zone = any(zone.colliderect(player.rect) for zone in self.gravity_zones)
        self.current_gravity = -1 if in_reverse_zone else 1

        speed = 310
        move_x = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move_x -= speed
            player.facing = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move_x += speed
            player.facing = 1
        player.set_motion_state(abs(move_x) > 0, dt)

        grounded = player.on_ground
        if grounded and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]):
            player.vel.y = player.jump_strength * self.current_gravity
            player.on_ground = False

        previous = player.rect.copy()
        player.rect.x += int(move_x * dt)
        collision_platforms = self.active_platforms()
        if player.reveal_active:
            collision_platforms += self.hidden_platforms
        for platform in collision_platforms:
            if player.rect.colliderect(platform):
                if move_x > 0:
                    player.rect.right = platform.left
                elif move_x < 0:
                    player.rect.left = platform.right

        player.vel.y += self.gravity * self.current_gravity * dt
        player.rect.y += int(player.vel.y * dt)
        player.on_ground = False
        for platform in collision_platforms:
            if player.rect.colliderect(platform):
                if self.current_gravity > 0 and previous.bottom <= platform.top and player.vel.y >= 0:
                    player.rect.bottom = platform.top
                    player.vel.y = 0
                    player.on_ground = True
                elif self.current_gravity < 0 and previous.top >= platform.bottom and player.vel.y <= 0:
                    player.rect.top = platform.bottom
                    player.vel.y = 0
                    player.on_ground = True

        if player.rect.top > HEIGHT + 180 or player.rect.bottom < -180:
            player.health = 0

        for platform in self.moving_platforms:
            platform["time"] += dt
            blend = (math.sin(platform["time"] * 1.4) + 1) / 2
            pos = platform["start"].lerp(platform["end"], blend)
            platform["rect"].topleft = (round(pos.x), round(pos.y))

        # Enemy / hazard interactions for level 2: spikes and puzzle gates.
        for spike in self.spikes:
            if player.rect.colliderect(spike) and player.apply_damage():
                self.particles.append(FloatText("-1", player.rect.x, player.rect.y - 20, CRIMSON))
                player.vel.y = -300 if self.current_gravity > 0 else 300

        for cipher in self.ciphers:
            if not cipher["solved"] and player.rect.colliderect(cipher["rect"]) and player.reveal_active:
                cipher["solved"] = True
                self.particles.append(FloatText("Cipher solved", cipher["rect"].x, cipher["rect"].y - 20, CYAN))

        for page in self.pages:
            if page["taken"]:
                continue
            visible = (not page["hidden"]) or player.reveal_active
            behind_cipher = page["rect"].x > 850 and page["rect"].x < 940 and not self.ciphers[0]["solved"]
            behind_cipher = behind_cipher or (page["rect"].x > 1750 and page["rect"].x < 1880 and not self.ciphers[1]["solved"])
            if visible and not behind_cipher and player.rect.colliderect(page["rect"]):
                page["taken"] = True
                self.collected += 1
                self.particles.append(FloatText("Decoded page", page["rect"].x, page["rect"].y - 24, AMBER))

        self.camera_x = clamp(player.rect.centerx - WIDTH // 2, 0, self.length - WIDTH)
        self.particles = [p for p in self.particles if p.update(dt)]
        # Level 2 completion condition: collect every page and reach the exit side.
        if self.collected >= self.target_pages and player.rect.centerx > 2360:
            self.done = True
        return "lose" if player.health <= 0 else ("next" if self.done else None)

    def draw(self, surface, fonts, backgrounds=None):
        bunker_bg = backgrounds.get("bunker") if backgrounds else None
        if not draw_level_background(surface, bunker_bg, self.camera_x, self.length - WIDTH):
            draw_bunker_background(surface, self.camera_x, self.current_gravity < 0)
        for zone in self.gravity_zones:
            rect = zone.move(-self.camera_x, 0)
            glow = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (110, 77, 215, 45), glow.get_rect(), border_radius=20)
            surface.blit(glow, rect.topleft)
        bunker_palette = {
            "top": (104, 118, 132),
            "mid": (76, 86, 102),
            "shadow": (47, 53, 68),
            "crack": (58, 69, 86),
            "highlight": (166, 180, 192),
            "accent": (95, 107, 123),
        }
        for platform in self.platforms:
            draw_stone_surface(surface, platform.move(-self.camera_x, 0), bunker_palette, self.camera_x, border_radius=5)
        for platform in self.moving_platforms:
            draw_stone_surface(surface, platform["rect"].move(-self.camera_x, 0), bunker_palette, self.camera_x + 60, border_radius=5)
        for hidden in self.hidden_platforms:
            rect = hidden.move(-self.camera_x, 0)
            if self.player.reveal_active:
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
        for cipher in self.ciphers:
            rect = cipher["rect"].move(-self.camera_x, 0)
            color = CYAN if cipher["solved"] else (106, 145, 176)
            pygame.draw.rect(surface, color, rect, border_radius=8)
            text = fonts["small"].render("#?", True, BLACK)
            surface.blit(text, (rect.x + 12, rect.y + 12))
            if not cipher["solved"]:
                hint = fonts["tiny"].render(cipher["hint"], True, MIST)
                surface.blit(hint, (rect.x - 30, rect.y - 20))
        for page in self.pages:
            if page["taken"]:
                continue
            if page["hidden"] and not self.player.reveal_active:
                continue
            draw_page(surface, page["rect"].x - self.camera_x, page["rect"].y)
        self.player.draw(surface, self.camera_x)
        draw_hud(surface, fonts, self.player, self.collected, self.target_pages, 2, self.message)
        badge = fonts["small"].render("Inverted gravity" if self.current_gravity < 0 else "Normal gravity", True, WHITE)
        surface.blit(badge, (WIDTH - 220, 88))
        for particle in self.particles:
            alpha = int(255 * clamp(particle.life / 1.4, 0, 1))
            text = fonts["small"].render(particle.text, True, particle.color)
            text.set_alpha(alpha)
            surface.blit(text, (particle.x - self.camera_x, particle.y))


class BossLevel:
    def __init__(self):
        self.reset()

    def reset(self):
        self.player = Player()
        self.player.reset_position(120, GROUND_Y - 78)
        self.player.health = 6
        self.player.max_health = 6
        self.message = "Level 3: Survive Bill's shadow, reveal weak points, then charge the portal with Stan."
        self.particles = []
        self.platforms = [
            pygame.Rect(250, 460, 180, 24),
            pygame.Rect(520, 360, 170, 24),
            pygame.Rect(850, 450, 180, 24),
        ]
        self.hidden_platforms = [
            pygame.Rect(690, 280, 120, 20),
            pygame.Rect(1020, 300, 120, 20),
        ]
        self.boss_rect = pygame.Rect(920, 140, 160, 190)
        self.boss_health = 12
        self.boss_fire_timer = 1.1
        self.distortion = 0.0
        self.projectiles = []
        self.weak_points = []
        self.weak_timer = 2.8
        self.stan_ready = False
        self.stan_rect = pygame.Rect(1090, GROUND_Y - 82, 46, 82)
        self.portal_rect = pygame.Rect(1120, 430, 88, 170)
        self.win = False

    def spawn_projectile(self):
        origin = pygame.Vector2(self.boss_rect.centerx, self.boss_rect.centery)
        target = pygame.Vector2(self.player.rect.centerx, self.player.rect.centery)
        direction = target - origin
        if direction.length() == 0:
            direction = pygame.Vector2(-1, 0)
        direction = direction.normalize()
        direction.rotate_ip(random.uniform(-18, 18))
        self.projectiles.append({"pos": pygame.Vector2(origin), "vel": direction * random.uniform(260, 380), "radius": random.randint(12, 18)})

    def spawn_weak_point(self):
        if len(self.weak_points) >= 2:
            return
        pool = [
            pygame.Rect(620, 210, 34, 34),
            pygame.Rect(760, 200, 34, 34),
            pygame.Rect(870, 280, 34, 34),
            pygame.Rect(1030, 215, 34, 34),
            pygame.Rect(760, 420, 34, 34),
        ]
        rect = random.choice(pool).copy()
        if any(item["rect"].colliderect(rect) for item in self.weak_points):
            return
        self.weak_points.append({"rect": rect, "life": 4.0})

    def update(self, dt, keys):
        player = self.player
        player.update_common(dt)
        player.reveal_active = keys[pygame.K_f] and player.reveal_energy > 0.2

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

        previous = player.rect.copy()
        player.rect.x += int(move_x * dt)
        player.rect.x = clamp(player.rect.x, 20, WIDTH - player.rect.width - 20)

        collision_platforms = list(self.platforms)
        if player.reveal_active:
            collision_platforms += self.hidden_platforms
        for platform in collision_platforms:
            if player.rect.colliderect(platform):
                if move_x > 0:
                    player.rect.right = platform.left
                elif move_x < 0:
                    player.rect.left = platform.right

        player.vel.y += 1650 * dt
        player.rect.y += int(player.vel.y * dt)
        player.on_ground = False
        for platform in collision_platforms + [pygame.Rect(0, GROUND_Y, WIDTH, 120)]:
            if player.rect.colliderect(platform) and previous.bottom <= platform.top and player.vel.y >= 0:
                player.rect.bottom = platform.top
                player.vel.y = 0
                player.on_ground = True

        self.boss_fire_timer -= dt
        if self.boss_fire_timer <= 0 and not self.stan_ready:
            self.spawn_projectile()
            self.boss_fire_timer = 0.95 if self.boss_health > 5 else 0.68
        # Enemy attack logic for level 3: boss projectiles and weak-point phases.
        for projectile in list(self.projectiles):
            projectile["pos"] += projectile["vel"] * dt
            if projectile["pos"].x < -80 or projectile["pos"].x > WIDTH + 80 or projectile["pos"].y < -80 or projectile["pos"].y > HEIGHT + 80:
                self.projectiles.remove(projectile)
                continue
            rect = pygame.Rect(projectile["pos"].x - projectile["radius"], projectile["pos"].y - projectile["radius"], projectile["radius"] * 2, projectile["radius"] * 2)
            if player.rect.colliderect(rect):
                if player.apply_damage():
                    self.particles.append(FloatText("-1", player.rect.x, player.rect.y - 18, CRIMSON))
                self.projectiles.remove(projectile)

        self.weak_timer -= dt
        if self.weak_timer <= 0 and not self.stan_ready:
            self.spawn_weak_point()
            self.weak_timer = random.uniform(2.2, 3.3)
        for point in list(self.weak_points):
            point["life"] -= dt
            if point["life"] <= 0:
                self.weak_points.remove(point)
                continue
            if player.reveal_active and player.rect.colliderect(point["rect"]):
                self.weak_points.remove(point)
                self.boss_health -= 1
                self.distortion = 0.6
                self.particles.append(FloatText("Weak point broken", point["rect"].x - 30, point["rect"].y - 20, CYAN))

        self.distortion = max(0.0, self.distortion - dt)
        if self.boss_health <= 0:
            self.stan_ready = True
        if self.stan_ready and player.rect.colliderect(self.stan_rect):
            self.stan_ready = "met"
        close_to_portal = player.rect.colliderect(self.portal_rect.inflate(30, 30))
        if self.stan_ready and close_to_portal and keys[pygame.K_e]:
            player.portal_charge += dt
            if player.portal_charge >= 3.2:
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
        if not draw_level_background(surface, boss_bg):
            draw_boss_background(surface, self.distortion)
        arena_floor = pygame.Rect(0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y)
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
            border_radius=0,
        )
        for platform in self.platforms:
            draw_stone_surface(
                surface,
                platform,
                {
                    "top": (95, 106, 132),
                    "mid": (66, 74, 98),
                    "shadow": (35, 40, 56),
                    "crack": (114, 126, 154),
                    "highlight": (163, 175, 201),
                    "accent": (84, 94, 120),
                },
                border_radius=6,
            )
        for platform in self.hidden_platforms:
            if self.player.reveal_active:
                draw_stone_surface(
                    surface,
                    platform,
                    {
                        "top": (212, 226, 232),
                        "mid": (182, 198, 208),
                        "shadow": (129, 145, 160),
                        "crack": (126, 148, 168),
                        "highlight": (242, 246, 249),
                        "accent": (168, 218, 228),
                    },
                    border_radius=6,
                )
            else:
                pygame.draw.rect(surface, (91, 145, 152), platform, 1, border_radius=6)
        draw_portal(surface, self.portal_rect, self.player.portal_charge / 3.2)
        if not self.stan_ready:
            draw_bill_shadow(surface, self.boss_rect, self.boss_health)
        else:
            draw_stan(surface, self.stan_rect)
        for projectile in self.projectiles:
            pygame.draw.circle(surface, (114, 245, 255), projectile["pos"], projectile["radius"])
            pygame.draw.circle(surface, WHITE, projectile["pos"], max(5, projectile["radius"] // 2))
        for point in self.weak_points:
            color = CYAN if self.player.reveal_active else (71, 103, 111)
            pygame.draw.circle(surface, color, point["rect"].center, 18, 3)
            pygame.draw.circle(surface, color, point["rect"].center, 6)
        self.player.draw(surface)
        draw_hud(surface, fonts, self.player, max(0, 12 - self.boss_health), 12, 3, self.message)
        boss_text = fonts["small"].render(f"Bill's shadow: {max(0, self.boss_health)}/12", True, WHITE)
        surface.blit(boss_text, (WIDTH - 240, 88))
        if self.stan_ready:
            text = fonts["small"].render("Hold E near portal to escape", True, AMBER)
            surface.blit(text, (WIDTH // 2 - text.get_width() // 2, 110))
        for particle in self.particles[-4:]:
            alpha = int(255 * clamp(particle.life / 1.4, 0, 1))
            text = fonts["small"].render(particle.text, True, particle.color)
            text.set_alpha(alpha)
            surface.blit(text, (particle.x, particle.y))


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
    pygame.draw.ellipse(surface, (194, 56, 61), rect)
    pygame.draw.circle(surface, (240, 213, 184), (rect.x + 22, rect.y + 20), 11)
    pygame.draw.polygon(surface, WHITE, [(rect.x + 12, rect.y + 26), (rect.x + 32, rect.y + 26), (rect.x + 22, rect.bottom)])
    pygame.draw.circle(surface, BLACK, (rect.x + 18, rect.y + 18), 2)
    pygame.draw.circle(surface, BLACK, (rect.x + 26, rect.y + 18), 2)


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

    # Keep a distant lower-wall base, but place it well below the playable
    # platform line so it does not read as solid ground across the whole level.
    floor = pygame.Rect(0, 612, WIDTH, HEIGHT - 612)
    draw_stone_surface(
        surface,
        floor,
        {
            "top": (78, 88, 104) if not inverted else (88, 74, 102),
            "mid": (53, 60, 77),
            "shadow": (26, 31, 42),
            "crack": (71, 82, 100),
            "highlight": (128, 139, 156),
            "accent": (64, 74, 88),
        },
        camera_x,
        border_radius=0,
    )


def draw_spikes(surface, rect):
    points = []
    step = max(1, rect.width // 5)
    for x in range(rect.x, rect.right + 1, step):
        points.extend([(x, rect.bottom), (x + step // 2, rect.y), (x + step, rect.bottom)])
    pygame.draw.polygon(surface, (196, 102, 92), points)


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
    panel = pygame.Rect(16, 14, WIDTH - 32, 82)
    hud = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(hud, (9, 12, 18, 180), hud.get_rect(), border_radius=20)
    surface.blit(hud, panel.topleft)
    surface.blit(fonts["small"].render(f"Level {level_index}", True, WHITE), (30, 26))
    surface.blit(fonts["small"].render(f"Pages / progress: {collected}/{total}", True, PAPER), (30, 52))
    for i in range(player.max_health):
        color = CRIMSON if i < player.health else (70, 46, 52)
        pygame.draw.rect(surface, color, (280 + i * 28, 26, 20, 20), border_radius=6)
    surface.blit(fonts["tiny"].render("Diary lens / flashlight", True, WHITE), (280, 55))
    pygame.draw.rect(surface, (44, 59, 78), (450, 57, 180, 12), border_radius=6)
    pygame.draw.rect(surface, AMBER, (450, 57, int(180 * player.reveal_energy / player.max_reveal), 12), border_radius=6)
    surface.blit(fonts["tiny"].render(message, True, MIST), (660, 34))


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
            "settings_background": first_existing(os.path.join(IMAGES_DIR, "settings_background.png"), os.path.join(IMAGES_DIR, "settings_background.jpg")),
            "forest_background": first_existing(os.path.join(IMAGES_DIR, "forest_background.png"), os.path.join(IMAGES_DIR, "forest_background.jpg")),
            "bunker_background": first_existing(os.path.join(IMAGES_DIR, "bunker_background.png"), os.path.join(IMAGES_DIR, "bunker_background.jpg")),
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
        }
        self.level_factories = [ForestLevel, BunkerLevel, BossLevel]
        self.state = "menu"
        self.levels = self.build_levels()
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
        }
        self.ui_images = {
            "menu_background": load_scaled_image(self.asset_paths["menu_background"], (WIDTH, HEIGHT)),
            "settings_background": load_scaled_image(self.asset_paths["settings_background"], (WIDTH, HEIGHT)),
        }
        self.level_backgrounds = {
            "forest": load_image(self.asset_paths["forest_background"]),
            "bunker": load_image(self.asset_paths["bunker_background"]),
            "boss": load_image(self.asset_paths["boss_background"]),
            "forest_layers": load_parallax_layers("forest", 12),
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
        self.start_music()
        self.apply_difficulty()

    def build_levels(self):
        return [factory() for factory in self.level_factories]

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
        section_gap = 18

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

        music_size = self.get_music_toggle_reference_size()
        if music_size:
            music_w, music_h = fit_size(music_size, (250, 116))
        else:
            music_w, music_h = 250, 96

        slider_gap = 10
        slider_label_gap = 42
        slider_w = max(150, content_width - music_w - slider_gap)
        slider_bar_image = crop_visible_bounds(self.settings_images["slider_bar"])
        if slider_bar_image:
            slider_ratio = slider_bar_image.get_width() / max(1, slider_bar_image.get_height())
            slider_h = int(clamp(slider_w / max(slider_ratio, 0.1), 22, 32))
        else:
            slider_h = 22

        slider_total_h = slider_h + slider_label_gap
        bottom_group_h = max(music_h, slider_total_h)
        bottom_y = content_bottom - bottom_group_h
        combined_w = music_w + slider_gap + slider_w
        bottom_left = content_left + max(0, (content_width - combined_w) // 2)
        music_y = bottom_y + (bottom_group_h - music_h) // 2
        slider_y = bottom_y + slider_label_gap
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
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            self.start_music()
        else:
            pygame.mixer.music.stop()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)

    def reset_level(self, index=None):
        target_index = self.level_index if index is None else index
        self.levels[target_index] = self.level_factories[target_index]()
        settings = {
            0: {"health": 7, "reveal": 6.4, "forest_spawn_scale": 1.18},
            1: {"health": 5, "reveal": 5.5, "forest_spawn_scale": 1.0},
            2: {"health": 4, "reveal": 4.7, "forest_spawn_scale": 0.86},
        }
        self.apply_difficulty_to_level(self.levels[target_index], settings[self.difficulty_index])

    def restart_all(self, clear_save=True):
        self.levels = self.build_levels()
        self.level_index = 0
        self.state = "menu"
        self.overlay_text = "Level 1"
        self.banner_timer = 4.0
        self.death_timer = 0.0
        self.death_message = ""
        self.settings_return_state = "menu"
        self.apply_difficulty()
        if clear_save:
            self.clear_progress()

    def start_death_restart(self):
        self.state = "death_notice"
        self.death_timer = 2.0
        self.death_message = f"You died. Restarting level {self.level_index + 1}..."

    def finish_death_restart(self):
        self.reset_level(self.level_index)
        self.state = "playing"
        self.overlay_text = f"Level {self.level_index + 1}"
        self.banner_timer = 2.2

    def start_new_game(self):
        self.levels = self.build_levels()
        self.level_index = 0
        self.apply_difficulty()
        self.clear_progress()
        self.state = "playing"
        self.overlay_text = "Level 1"
        self.banner_timer = 3.0
        self.death_timer = 0.0
        self.death_message = ""
        self.settings_return_state = "menu"

    def continue_game(self):
        self.level_index = self.load_progress()
        self.levels = self.build_levels()
        self.apply_difficulty()
        self.state = "playing"
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

    def draw_death_notice(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 190))
        self.screen.blit(overlay, (0, 0))
        title = self.fonts["title"].render("You Died", True, CRIMSON)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 240))
        subtitle = self.fonts["small"].render(self.death_message, True, WHITE)
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 320))

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

    # --- MAIN MENU ---
    def draw_menu(self):
        if self.ui_images["menu_background"]:
            self.screen.blit(self.ui_images["menu_background"], (0, 0))
        else:
            draw_forest_background(self.screen, 0)
        mouse_pos = pygame.mouse.get_pos()
        self.build_menu_buttons()
        for key in ("play", "continue", "settings", "exit"):
            self.draw_menu_button(key, mouse_pos)

    def draw_pause_menu(self):
        self.current_level.draw(self.screen, self.fonts, self.level_backgrounds)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 10, 18, 178))
        self.screen.blit(overlay, (0, 0))

        title = self.fonts["title"].render("Paused", True, WHITE)
        subtitle = self.fonts["small"].render("Esc to continue", True, PAPER)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 208))

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
        if self.is_point_on_settings_button("difficulty_left", mouse_pos):
            self.difficulty_index = (self.difficulty_index - 1) % len(self.difficulty_options)
            self.restart_all()
            self.state = "settings"
            return
        if self.is_point_on_settings_button("difficulty_right", mouse_pos):
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
        heading = "The diary is decoded. The twins escape." if victory else "The bunker wins this round."
        color = AMBER if victory else CRIMSON
        title = self.fonts["title"].render(heading, True, color)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 210))
        lines = ["Press R to restart the whole adventure.", "Press Esc to close the game."]
        if victory:
            lines.insert(0, "Stan opens the tear, the portal stabilizes, and Bill's shadow fades.")
        for i, line in enumerate(lines):
            text = self.fonts["small"].render(line, True, WHITE)
            self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, 320 + i * 42))

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
            self.level_index += 1
            if self.level_index >= len(self.levels):
                self.clear_progress()
                self.state = "victory"
            else:
                self.save_progress()
                self.banner_timer = 3.0
                self.overlay_text = f"Level {self.level_index + 1}"
        elif result == "lose":
            self.start_death_restart()
        elif result == "win":
            self.clear_progress()
            self.state = "victory"

    def draw_banner(self):
        if self.banner_timer <= 0:
            return
        alpha = int(255 * min(1.0, self.banner_timer))
        text = self.overlay_text or f"Level {self.level_index + 1}"
        banner = self.fonts["title"].render(text, True, WHITE)
        banner.set_alpha(alpha)
        self.screen.blit(banner, (WIDTH // 2 - banner.get_width() // 2, 130))

    # --- MAIN LOOP ---
    def run(self):
        self.overlay_text = "Level 1"
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
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
                if result:
                    self.handle_result(result)
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
        pygame.quit()


if __name__ == "__main__":
    Game().run()

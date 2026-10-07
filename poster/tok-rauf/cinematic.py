"""Gred sinematik untuk poster 'Pusat Data AI Tanjung Bidara'.

Guna: python3 cinematic.py <input.jpg> <output.jpg>
Hanya rupa yang berubah (warna, cahaya, grain) — teks dan susunan kekal.
"""
import sys

import numpy as np
from PIL import Image, ImageFilter

SUN = (210, 520)  # pusat cahaya matahari di ufuk (x, y)


def blur(arr, radius):
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def main(src, dst):
    img = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lum = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)

    # 1. Gred teal & oren: bayang ke teal, cahaya ke ambar, kulit dilindungi
    shadow = (1 - smoothstep(0.0, 0.55, lum))[..., None]
    high = smoothstep(0.45, 1.0, lum)[..., None]
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    skin = ((r > g) & (g > b) & (r - b > 0.12) & (r - b < 0.5)).astype(np.float32)
    skin = blur(np.repeat(skin[..., None], 3, 2), 3)[..., :1]
    teal = np.array([-0.06, 0.02, 0.07], np.float32)
    amber = np.array([0.07, 0.025, -0.06], np.float32)
    img = img + shadow * teal * (1 - 0.7 * skin) + high * amber

    # 2. Lengkung S filem + hitam diangkat sedikit (rupa "fade")
    img = np.clip(img, 0, 1)
    img = img + 0.22 * (img - 0.5) * (1 - np.abs(2 * img - 1))
    img = 0.035 + img * 0.955

    # 3. Kabus matahari: cahaya hangat jejarian dari ufuk
    d = np.hypot(xx - SUN[0], (yy - SUN[1]) * 1.6)
    glow = np.exp(-(d / 380) ** 2)[..., None]
    img = img + glow * np.array([0.30, 0.17, 0.05], np.float32) * 0.55

    # 4. Suar anamorfik: jalur mendatar melalui matahari, pudar sebelum subjek
    dy = np.abs(yy - SUN[1])
    fade = 1 - smoothstep(330, 420, xx)
    streak = np.exp(-(dy / 2.5) ** 2) * np.exp(-np.abs(xx - SUN[0]) / 260)
    streak += 0.35 * np.exp(-(dy / 12.0) ** 2) * np.exp(-np.abs(xx - SUN[0]) / 200)
    img = img + (streak * fade)[..., None] * np.array([0.55, 0.42, 0.30], np.float32) * 0.6

    # 5. Bloom: kecerahan tinggi (tajuk emas, langit) melimpah lembut
    bright = np.clip(img - 0.72, 0, 1) / 0.28
    bloom = blur(bright, 18) * 0.35 + blur(bright, 6) * 0.25
    img = 1 - (1 - img) * (1 - bloom * np.array([1.0, 0.85, 0.65], np.float32))

    # 6. Abrasi kromatik halus di tepi
    off = 2
    edge = smoothstep(0.35, 0.75, np.hypot((xx - w / 2) / w, (yy - h / 2) / h))
    rs = np.roll(img[..., 0], off, axis=1)
    bs = np.roll(img[..., 2], -off, axis=1)
    img[..., 0] = img[..., 0] * (1 - edge) + rs * edge
    img[..., 2] = img[..., 2] * (1 - edge) + bs * edge

    # 7. Vignet oval
    v = np.hypot((xx - w / 2) / (w * 0.62), (yy - h * 0.5) / (h * 0.72))
    img = img * (1 - 0.45 * smoothstep(0.6, 1.3, v))[..., None]

    # 8. Grain filem (lebih ketara di ton tengah)
    rng = np.random.default_rng(7)
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    grain = 0.7 * grain + 0.3 * blur(np.repeat(grain[..., None] * 0.25 + 0.5, 3, 2), 1)[..., 0]
    lum = np.clip(img, 0, 1) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    amt = 0.028 * (1 - np.abs(2 * lum - 1)) + 0.010
    img = img + (grain * amt)[..., None]

    out = Image.fromarray(np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8))
    out.save(dst, quality=95, subsampling=0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

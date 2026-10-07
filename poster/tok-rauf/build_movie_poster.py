"""Bina semula poster 'Pusat Data AI Tanjung Bidara' gaya poster wayang.

Guna: python3 build_movie_poster.py
Input : Pusat_Data_AI_asal.jpg (latar pantai), subjek_mikrofon.png (potongan
        subjek RGBA dari potret_mikrofon.jpg), subjek.png (potongan subjek
        lama, hanya untuk membersihkan latar)
Output: Pusat_Data_AI_wayang.jpg (1080x1350) + Pusat_Data_AI_wayang_2x.jpg

Wording hanya dari poster asal.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
W, H, S = 1080, 1350, 2  # kanvas asas, dirender pada skala S

# Latar: adegan pantai poster asal dari y=BG_TOP hingga BG_CUT (di bawah
# teks atas, di atas kotak judul lama), dibesarkan memenuhi kanvas dan
# dipotong dari x=BG_X supaya matahari kekal di kiri.
BG_TOP, BG_CUT, BG_X = 150, 880, 210
BG_K = H / (BG_CUT - BG_TOP)

# Subjek: dibesarkan, tepi bawah gambar = tepi bawah poster.
SUBJECT = dict(file="subjek_mikrofon.png", scale=1.6, x=36)

GOLD_MID = (232, 170, 82)
CREAM = (246, 240, 228)
GOLD = [(0, (255, 236, 190)), (0.45, (255, 210, 130)), (0.52, GOLD_MID),
        (0.8, (190, 112, 40)), (1, (150, 82, 28))]
SILVER = [(0, (255, 255, 255)), (0.5, (238, 240, 244)), (0.56, (200, 208, 218)),
          (1, (160, 170, 184))]
LUM = np.array([0.2126, 0.7152, 0.0722], np.float32)


# ---------------------------------------------------------------- utiliti

def font(name, size, var=None):
    f = ImageFont.truetype(str(FONTS / name), int(size * S))
    if var is not None:
        f.set_variation_by_axes([var])
    return f


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def tracked_width(text, f, track):
    return sum(f.getlength(c) for c in text) + track * S * (len(text) - 1)


def draw_tracked(draw, xy, text, f, fill, track=0.0, anchor="center"):
    """Teks dengan jarak huruf (tracking). xy dalam koordinat asas."""
    x, y = xy[0] * S, xy[1] * S
    w = tracked_width(text, f, track)
    if anchor == "center":
        x -= w / 2
    for c in text:
        draw.text((x, y), c, font=f, fill=fill, anchor="ls")
        x += f.getlength(c) + track * S
    return w / S


def text_mask(items):
    """items: senarai (xy, text, font, track). Pulangkan topeng L."""
    m = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(m)
    for xy, text, f, track in items:
        draw_tracked(d, xy, text, f, 255, track)
    return m


def vgrad(n, stops):
    t = np.linspace(0, 1, n)
    out = np.zeros((n, 3), np.float32)
    for c in range(3):
        out[:, c] = np.interp(t, [s[0] for s in stops], [s[1][c] for s in stops])
    return out / 255


def screen(base, a, col):
    return 1 - (1 - base) * (1 - a * np.asarray(col, np.float32))


def drop_shadow(base, mask, radius=6, k=0.75):
    """Bayang lembut di bawah teks supaya terbaca atas latar terang."""
    sh = np.asarray(mask.filter(ImageFilter.GaussianBlur(radius * S)), np.float32)
    sh = np.clip(sh / 255 * 1.6, 0, 1)[..., None]
    return base * (1 - k * sh)


def metal(base, items, y0, y1, stops, glow_col=None, glow_r=0, glow_k=0.0,
          shadow=(6, 0.75)):
    """Isi teks dengan kecerunan logam menegak + bayang + glow."""
    m = text_mask(items)
    a = np.asarray(m, np.float32)[..., None] / 255
    grad = vgrad(int((y1 - y0) * S), stops)
    col = np.empty_like(base)
    i0 = int(y0 * S)
    col[:i0] = grad[0]
    col[i0:i0 + len(grad)] = grad[:, None, :]
    col[i0 + len(grad):] = grad[-1]
    if shadow:
        base = drop_shadow(base, m, *shadow)
    if glow_col is not None:
        g = np.asarray(m.filter(ImageFilter.GaussianBlur(glow_r * S)), np.float32)
        base = screen(base, (g / 255 * glow_k)[..., None], np.array(glow_col) / 255)
    return base * (1 - a) + col * a


def to_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))


# ---------------------------------------------------------------- latar

def fill_rows(img, mask):
    """Isi kawasan bertopeng secara mendatar dengan piksel bersih terdekat
    di kirinya, jadi langit & laut di kiri bersambung ke kanan."""
    out = img.astype(np.float32).copy()
    for y in np.where(mask.any(1))[0]:
        row = mask[y]
        xs = np.where(~row)[0]
        if len(xs) == 0:
            continue
        idx = np.where(row)[0]
        left = np.searchsorted(xs, idx) - 1
        src = np.where(left >= 0, xs[np.clip(left, 0, None)], xs[0])
        out[y, idx] = out[y, src]
    return out


def background():
    src = cv2.cvtColor(cv2.imread(str(HERE / "Pusat_Data_AI_asal.jpg")), cv2.COLOR_BGR2RGB)
    # buang subjek lama (potongan asal pada y=300) beserta halonya
    old = cv2.imread(str(HERE / "subjek.png"), cv2.IMREAD_UNCHANGED)[..., 3]
    om = np.zeros(src.shape[:2], np.uint8)
    om[300:300 + old.shape[0], :old.shape[1]] = (old > 10) * 255
    om = cv2.dilate(om, np.ones((31, 31), np.uint8)) > 0
    # seluruh kanan di bawah pelepah juga diganti supaya tiada sempadan
    om[380:, 175:] = True
    filled = fill_rows(src, om)
    soft = cv2.GaussianBlur(filled, (0, 0), 14)
    m = cv2.GaussianBlur(om.astype(np.float32), (0, 0), 14)[..., None]
    img = filled * (1 - m) + soft * m
    img = np.clip(img[BG_TOP:BG_CUT], 0, 255).astype(np.uint8)
    im = Image.fromarray(img).resize((int(W * BG_K * S), H * S), Image.LANCZOS)
    im = im.crop((int(BG_X * S), 0, int(BG_X * S) + W * S, H * S))
    im = im.filter(ImageFilter.GaussianBlur(2.0 * S))  # kedalaman medan
    return np.asarray(im, np.float32) / 255


def subject_layer():
    sub = Image.open(HERE / SUBJECT["file"]).convert("RGBA")
    k = SUBJECT["scale"] * S
    sub = sub.resize((int(sub.width * k), int(sub.height * k)), Image.LANCZOS)
    layer = Image.new("RGBA", (W * S, H * S))
    layer.alpha_composite(sub, (int(SUBJECT["x"] * S), H * S - sub.height))
    arr = np.asarray(layer, np.float32) / 255
    a = cv2.erode(arr[..., 3], np.ones((2 * S, 2 * S), np.uint8))  # buang halo
    a = cv2.GaussianBlur(a, (0, 0), 0.7 * S)
    return arr[..., :3], a


def grade(img):
    lum = img @ LUM
    sh = (1 - smoothstep(0.0, 0.6, lum))[..., None]
    hi = smoothstep(0.45, 1.0, lum)[..., None]
    img = img + sh * np.array([-0.03, 0.01, 0.04]) + hi * np.array([0.05, 0.02, -0.05])
    img = np.clip(img, 0, 1)
    img = img + 0.12 * (img - 0.5) * (1 - np.abs(2 * img - 1))
    return np.clip(img, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- komposisi

def main():
    bg = grade(background())
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32) / S

    # cahaya matahari & suar anamorfik di ufuk kiri
    sun = (205 * BG_K - BG_X, (520 - BG_TOP) * BG_K)
    d = np.hypot(xx - sun[0], (yy - sun[1]) * 1.7)
    bg = screen(bg, np.exp(-(d / 380) ** 2)[..., None] * 0.5, (1.0, 0.62, 0.25))
    dy = np.abs(yy - sun[1])
    streak = (np.exp(-(dy / 2.2) ** 2) + 0.3 * np.exp(-(dy / 10) ** 2)) * \
        np.exp(-np.abs(xx - sun[0]) / 320)
    bg = screen(bg, streak[..., None] * 0.8, (1.0, 0.85, 0.65))

    # judul: PUSAT DATA di atas, AI gergasi di belakang kepala
    t1 = font("Cinzel[wght].ttf", 104, 800)
    bg = metal(bg, [((540, 352), "PUSAT DATA", t1, 8)], 274, 354, SILVER,
               (255, 255, 255), 14, 0.2)
    big = font("Cinzel[wght].ttf", 500, 900)
    bg = metal(bg, [((540, 800), "AI", big, 24)], 440, 800, GOLD,
               (255, 120, 30), 30, 0.45, shadow=(10, 0.55))

    # subjek: cahaya pinggir hangat dari arah matahari (kiri)
    srgb, sa = subject_layer()
    srgb = grade(srgb)
    edge = np.clip(sa - cv2.GaussianBlur(sa, (0, 0), 5 * S), 0, 1)
    side = 1 - smoothstep(350, 800, xx)
    rim = np.clip(edge * (0.25 + 0.75 * side) * 1.3, 0, 1)[..., None]
    srgb = screen(srgb, rim, (1.0, 0.72, 0.4))
    srgb = screen(srgb, (side * 0.10)[..., None], (1.0, 0.7, 0.4))
    shadow = cv2.GaussianBlur(sa, (0, 0), 24 * S)[..., None]
    img = bg * (1 - 0.25 * shadow)
    img = img * (1 - sa[..., None]) + srgb * sa[..., None]

    # vignet sangat ringan
    v = np.hypot((xx - W / 2) / (W * 0.6), (yy - H * 0.5) / (H * 0.65))
    img = img * (1 - 0.12 * smoothstep(0.7, 1.4, v))[..., None]

    img = typography(img)

    # bloom halus + grain filem
    bright = np.clip(img - 0.72, 0, 1) / 0.28
    bl = cv2.GaussianBlur(bright, (0, 0), 14 * S) * 0.35
    img = 1 - (1 - img) * (1 - bl * np.array([1, 0.8, 0.55], np.float32))
    grain = cv2.GaussianBlur(np.random.default_rng(11).normal(0, 1, (H * S, W * S))
                             .astype(np.float32), (0, 0), 0.6 * S)
    lum = np.clip(img, 0, 1) @ LUM
    img = img + (grain * (0.03 * (1 - np.abs(2 * lum - 1)) + 0.008))[..., None]
    out = to_img(img)
    out.save(HERE / "Pusat_Data_AI_wayang_2x.jpg", quality=94, subsampling=0)
    out.resize((W, H), Image.LANCZOS).save(HERE / "Pusat_Data_AI_wayang.jpg",
                                           quality=95, subsampling=0)


# ---------------------------------------------------------------- tipografi

def typography(base):
    # KISAH TOK RAUF: besar, TOK RAUF emas bercahaya
    k1 = font("Cinzel[wght].ttf", 50, 600)
    k2 = font("Cinzel[wght].ttf", 76, 900)
    w1 = tracked_width("KISAH", k1, 10) / S
    w2 = tracked_width("TOK RAUF", k2, 8) / S
    x = 540 - (w1 + 30 + w2) / 2
    base = metal(base, [((x + w1 / 2, 108), "KISAH", k1, 10)], 66, 108, SILVER)
    base = metal(base, [((x + w1 + 30 + w2 / 2, 108), "TOK RAUF", k2, 8)], 50, 110, GOLD,
                 (255, 130, 30), 16, 0.6)

    tag = font("CormorantGaramond[wght].ttf", 34, 600)
    lab = font("Oswald[wght].ttf", 18, 500)
    sub = font("Cinzel[wght].ttf", 40, 700)
    foot = font("Oswald[wght].ttf", 10, 400)
    t_a, t_b = "Kabel internet dunia naik ke darat ", "di pantai ini."
    credit = "FOTO LATAR: AKUUJANG / WIKIMEDIA COMMONS, CC BY-SA 4.0  ·  PUSAT DATA MASIH DIRANCANG"

    # bayang untuk teks biasa
    base = drop_shadow(base, text_mask([
        ((540, 162), t_a + t_b, tag, 1.0),
        ((540, 238), "TOK RAUF UMUM  ·  DIRANCANG", lab, 7),
        ((540, 1292), "TANJUNG BIDARA", sub, 16),
        ((540, 1334), credit, foot, 1.8)]), 5, 0.85)
    canvas = to_img(base)
    d = ImageDraw.Draw(canvas)

    wa = tracked_width(t_a, tag, 1.0) / S
    wb = tracked_width(t_b, tag, 1.0) / S
    x = 540 - (wa + wb) / 2
    draw_tracked(d, (x, 162), t_a, tag, CREAM, 1.0, anchor="left")
    draw_tracked(d, (x + wa, 162), t_b, tag, (255, 190, 100), 1.0, anchor="left")

    draw_tracked(d, (540, 238), "TOK RAUF UMUM  ·  DIRANCANG", lab, (255, 205, 130), 7)

    wsub = draw_tracked(d, (540, 1292), "TANJUNG BIDARA", sub, (255, 214, 150), 16)
    for sgn in (-1, 1):
        x0 = 540 + sgn * (wsub / 2 + 20)
        x1 = 540 + sgn * (wsub / 2 + 100)
        d.line([(x0 * S, 1278 * S), (x1 * S, 1278 * S)], fill=GOLD_MID, width=int(2 * S))

    draw_tracked(d, (540, 1334), credit, foot, (230, 230, 232), 1.8)
    return np.asarray(canvas, np.float32) / 255


if __name__ == "__main__":
    main()

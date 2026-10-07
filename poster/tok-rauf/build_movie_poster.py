"""Bina semula poster 'Pusat Data AI Tanjung Bidara' gaya poster wayang.

Guna: python3 build_movie_poster.py
Input : Pusat_Data_AI_asal.jpg (latar pantai), subjek.png (potongan subjek, RGBA)
Output: Pusat_Data_AI_wayang.jpg (1080x1350) + Pusat_Data_AI_wayang_2x.jpg (2160x2700)

Subjek ditetapkan dalam SUBJECT; tukar fail/skala/kedudukan di situ.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
W, H, S = 1080, 1350, 2  # kanvas asas, dirender pada skala S

# Subjek: fail, skala, kedudukan kiri-atas pada kanvas asas, dan julat
# pudar (y mula, y tamat) ke gelap di bawah.
SUBJECT = dict(file="subjek.png", scale=H / 880, pos=(-100, 300 * H / 880), fade=(1300, 1350))

# latar: adegan pantai (y < BG_CUT pada poster asal) dibesarkan memenuhi
# kanvas, dipotong dari x = BG_X supaya matahari kekal di kiri
BG_CUT, BG_X = 880, 100
BG_K = H / BG_CUT

GOLD_TOP = (255, 236, 190)
GOLD_MID = (232, 170, 82)
GOLD_LOW = (150, 82, 28)
CREAM = (238, 228, 210)
GREY = (150, 156, 166)


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
    elif anchor == "right":
        x -= w
    for c in text:
        draw.text((x, y), c, font=f, fill=fill, anchor="ls")
        x += f.getlength(c) + track * S
    return w / S


def text_mask(size, items):
    """items: senarai (xy, text, font, track). Pulangkan topeng L."""
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for xy, text, f, track in items:
        draw_tracked(d, xy, text, f, 255, track)
    return m


def vgrad(h, stops):
    """Kecerunan menegak RGB; stops = [(t, (r,g,b)), ...]."""
    t = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, 3), np.float32)
    ts = [s[0] for s in stops]
    for c in range(3):
        out[:, c] = np.interp(t[:, 0], ts, [s[1][c] for s in stops])
    return out


def drop_shadow(base, mask, radius=6, k=0.75):
    """Bayang lembut di bawah teks supaya terbaca atas latar terang."""
    sh = np.asarray(mask.filter(ImageFilter.GaussianBlur(radius * S)), np.float32)
    sh = np.clip(sh / 255 * 1.6, 0, 1)[..., None]
    return base * (1 - k * sh)


def glow(mask, radius, color, strength):
    g = mask.filter(ImageFilter.GaussianBlur(radius * S))
    a = (np.asarray(g, np.float32) / 255 * strength)[..., None]
    return a, np.array(color, np.float32) / 255


def screen(base, a, col):
    return 1 - (1 - base) * (1 - a * col)


# ---------------------------------------------------------------- latar

def background():
    src = cv2.imread(str(HERE / "Pusat_Data_AI_asal.jpg"))
    # buang teks lama di bahagian atas (tajuk & tagline) dengan inpaint
    hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
    med = cv2.medianBlur(src, 21)
    diff = np.abs(src.astype(int) - med.astype(int)).sum(2)
    band = np.zeros(src.shape[:2], bool)
    band[30:160, 150:930] = True
    mask = (band & ((diff > 40) | (hsv[..., 2] > 215))).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
    # subjek lama (potongan asal pada y=300) turut dibuang supaya tiada halo
    old = cv2.imread(str(HERE / "subjek.png"), cv2.IMREAD_UNCHANGED)[..., 3]
    om = np.zeros_like(mask)
    om[300:300 + old.shape[0], :old.shape[1]] = (old > 20).astype(np.uint8) * 255
    mask |= cv2.dilate(om, np.ones((25, 25), np.uint8))
    clean = cv2.inpaint(src, mask, 9, cv2.INPAINT_TELEA)
    img = cv2.cvtColor(clean, cv2.COLOR_BGR2RGB)
    img = img[:BG_CUT]
    k = H / BG_CUT
    im = Image.fromarray(img).resize((int(W * k * S), H * S), Image.LANCZOS)
    im = im.crop((int(BG_X * S), 0, int(BG_X * S) + W * S, H * S))
    # kedalaman medan: latar lembut sedikit supaya subjek terpisah
    im = im.filter(ImageFilter.GaussianBlur(2.2 * S))
    return np.asarray(im, np.float32) / 255


def subject_layer():
    sub = Image.open(HERE / SUBJECT["file"]).convert("RGBA")
    sw, sh = sub.size
    k = SUBJECT["scale"] * S
    sub = sub.resize((int(sw * k), int(sh * k)), Image.LANCZOS)
    layer = Image.new("RGBA", (W * S, H * S))
    px, py = SUBJECT["pos"]
    layer.alpha_composite(sub, (int(px * S), int(py * S)))
    arr = np.asarray(layer, np.float32) / 255
    rgb, a = arr[..., :3], arr[..., 3]
    # pudar ke gelap di bahagian bawah (subjek muncul dari bayang)
    yy = np.arange(H * S, dtype=np.float32)[:, None] / S
    f0, f1 = SUBJECT["fade"]
    a = a * (1 - smoothstep(f0, f1, yy))
    a = cv2.erode(a, np.ones((4 * S, 4 * S), np.uint8))  # buang halo tepi
    a = cv2.GaussianBlur(a, (0, 0), 0.8 * S)
    return rgb, a


def grade(img, lum_w=np.array([0.2126, 0.7152, 0.0722], np.float32)):
    lum = img @ lum_w
    sh = (1 - smoothstep(0.0, 0.6, lum))[..., None]
    hi = smoothstep(0.45, 1.0, lum)[..., None]
    img = img + sh * np.array([-0.03, 0.01, 0.04]) + hi * np.array([0.05, 0.02, -0.05])
    img = np.clip(img, 0, 1)
    img = img + 0.12 * (img - 0.5) * (1 - np.abs(2 * img - 1))
    return np.clip(img, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- komposisi

def main():
    bg = grade(background())
    h, w = H * S, W * S
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) / S

    # cahaya matahari & suar anamorfik di ufuk kiri
    sun = (205 * BG_K - BG_X, 520 * BG_K)
    d = np.hypot(xx - sun[0], (yy - sun[1]) * 1.7)
    bg = screen(bg, np.exp(-(d / 360) ** 2)[..., None] * 0.55,
                np.array([1.0, 0.62, 0.25], np.float32))
    dy = np.abs(yy - sun[1])
    streak = (np.exp(-(dy / 2.2) ** 2) + 0.3 * np.exp(-(dy / 10) ** 2)) * \
        np.exp(-np.abs(xx - sun[0]) / 300)
    bg = screen(bg, streak[..., None] * 0.8, np.array([1.0, 0.85, 0.65], np.float32))

    # huruf AI gergasi di langit, di belakang subjek
    bg = giant_ai(bg)

    # subjek dengan cahaya pinggir (rim light) hangat dari arah matahari
    srgb, sa = subject_layer()
    srgb = grade(srgb)
    edge = np.clip(sa - cv2.GaussianBlur(sa, (0, 0), 6 * S), 0, 1)
    side = 1 - smoothstep(380, 760, xx)  # sisi kiri lebih terang
    rim = (edge * (0.25 + 0.75 * side) * 1.4)[..., None]
    srgb = screen(srgb, np.clip(rim, 0, 1), np.array([1.0, 0.7, 0.35], np.float32))
    # bayang lembut di belakang subjek supaya tidak "terpampang"
    shadow = cv2.GaussianBlur(sa, (0, 0), 28 * S)[..., None]
    img = bg * (1 - 0.2 * shadow)
    img = img * (1 - sa[..., None]) + srgb * sa[..., None]

    # vignet sangat ringan
    v = np.hypot((xx - W / 2) / (W * 0.6), (yy - H * 0.5) / (H * 0.65))
    img = img * (1 - 0.15 * smoothstep(0.7, 1.4, v))[..., None]

    canvas = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    img = typography(canvas)

    # bloom + grain filem merentas seluruh poster
    arr = np.asarray(img, np.float32) / 255
    bright = np.clip(arr - 0.7, 0, 1) / 0.3
    bl = cv2.GaussianBlur(bright, (0, 0), 14 * S) * 0.4
    arr = 1 - (1 - arr) * (1 - bl * np.array([1, 0.8, 0.55], np.float32))
    rng = np.random.default_rng(11)
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    grain = cv2.GaussianBlur(grain, (0, 0), 0.6 * S)
    lum = arr @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    arr = arr + (grain * (0.03 * (1 - np.abs(2 * lum - 1)) + 0.008))[..., None]
    out = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
    out.save(HERE / "Pusat_Data_AI_wayang_2x.jpg", quality=94, subsampling=0)
    out.resize((W, H), Image.LANCZOS).save(HERE / "Pusat_Data_AI_wayang.jpg",
                                           quality=95, subsampling=0)


# ---------------------------------------------------------------- tipografi

def metal(base, items, y0, y1, stops, glow_col=None, glow_r=0, glow_k=0.0,
          opacity=1.0, fade=None):
    """Isi teks dengan kecerunan logam menegak + glow. Pulangkan base baharu."""
    size = (base.shape[1], base.shape[0])
    m = text_mask(size, items)
    a = np.asarray(m, np.float32)[..., None] / 255 * opacity
    if fade is not None:  # pudar bahagian bawah huruf ke dalam kabus
        yy = np.arange(base.shape[0], dtype=np.float32)[:, None, None] / S
        a = a * (1 - smoothstep(fade[0], fade[1], yy) * fade[2])
    grad = vgrad(int((y1 - y0) * S), stops) / 255
    col = np.empty_like(base)
    i0 = int(y0 * S)
    col[:i0] = grad[0]
    col[i0:i0 + len(grad)] = grad[:, None, :]
    col[i0 + len(grad):] = grad[-1]
    base = drop_shadow(base, m)
    if glow_col is not None:
        ga, gc = glow(m, glow_r, glow_col, glow_k)
        base = screen(base, ga, gc)
    return base * (1 - a) + col * a


GOLD = [(0, GOLD_TOP), (0.45, (255, 210, 130)), (0.52, GOLD_MID),
        (0.8, (190, 112, 40)), (1, GOLD_LOW)]
SILVER = [(0, (255, 255, 255)), (0.5, (236, 238, 242)), (0.56, (196, 204, 214)),
          (1, (150, 160, 175))]


def giant_ai(img):
    """Huruf 'AI' gergasi di belakang subjek."""
    f = font("Cinzel[wght].ttf", 470, 900)
    return metal(img, [((275, 735), "AI", f, 10)], 400, 735, GOLD,
                 (255, 120, 30), 30, 0.45, opacity=0.97)


def typography(canvas):
    base = np.asarray(canvas, np.float32) / 255

    # judul utama
    t1 = font("Cinzel[wght].ttf", 108, 800)
    base = metal(base, [((540, 1218), "PUSAT DATA", t1, 8)], 1138, 1220, SILVER,
                 (120, 170, 220), 18, 0.25)
    # KISAH TOK RAUF: besar, TOK RAUF emas bercahaya
    k1 = font("Cinzel[wght].ttf", 50, 600)
    k2 = font("Cinzel[wght].ttf", 74, 900)
    w1 = tracked_width("KISAH", k1, 10) / S
    w2 = tracked_width("TOK RAUF", k2, 8) / S
    gap = 30
    x = 540 - (w1 + gap + w2) / 2
    base = metal(base, [((x + w1 / 2, 112), "KISAH", k1, 10)], 70, 112, SILVER)
    base = metal(base, [((x + w1 + gap + w2 / 2, 112), "TOK RAUF", k2, 8)], 56, 114, GOLD,
                 (255, 130, 30), 16, 0.7)
    # bayang untuk teks biasa (tagline, label, sari kata, kredit)
    tag = font("CormorantGaramond[wght].ttf", 33, 500)
    lab = font("Oswald[wght].ttf", 17, 500)
    sub = font("Cinzel[wght].ttf", 38, 700)
    base = drop_shadow(base, text_mask((base.shape[1], base.shape[0]), [
        ((540, 168), "Kabel internet dunia naik ke darat di pantai ini.", tag, 1.0),
        ((540, 1106), "TOK RAUF UMUM  ·  DIRANCANG", lab, 7),
        ((540, 1284), "TANJUNG BIDARA", sub, 16)]), 5, 0.8)
    canvas = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(canvas)

    # atas: tagline (wording asal)
    a = "Kabel internet dunia naik ke darat "
    b = "di pantai ini."
    wa = tracked_width(a, tag, 1.0) / S
    wb = tracked_width(b, tag, 1.0) / S
    x = 540 - (wa + wb) / 2
    draw_tracked(d, (x, 168), a, tag, CREAM, 1.0, anchor="left")
    draw_tracked(d, (x + wa, 168), b, tag, (244, 178, 96), 1.0, anchor="left")

    # label kecil di atas judul
    draw_tracked(d, (540, 1106), "TOK RAUF UMUM  ·  DIRANCANG", lab, (232, 180, 110), 7)

    # TANJUNG BIDARA dengan garis emas
    wsub = draw_tracked(d, (540, 1284), "TANJUNG BIDARA", sub, CREAM, 16)
    for sgn in (-1, 1):
        x0 = 540 + sgn * (wsub / 2 + 22)
        x1 = 540 + sgn * (wsub / 2 + 110)
        d.line([(x0 * S, 1271 * S), (x1 * S, 1271 * S)], fill=GOLD_MID, width=int(1.5 * S))

    foot = font("Oswald[wght].ttf", 10, 400)
    draw_tracked(d, (540, 1330),
                 "FOTO: AKUUJANG / WIKIMEDIA COMMONS, CC BY-SA 4.0  ·  POTRET: UMNO ONLINE  ·  "
                 "PUSAT DATA MASIH DIRANCANG", foot, (225, 225, 228), 1.8)
    return canvas


if __name__ == "__main__":
    main()

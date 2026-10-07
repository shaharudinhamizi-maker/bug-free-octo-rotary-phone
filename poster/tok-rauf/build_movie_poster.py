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
SUBJECT = dict(file="subjek.png", scale=1.10, pos=(-56, 240), fade=(690, 900))

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
    im = Image.fromarray(img).resize((W * S, H * S), Image.LANCZOS)
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
    a = cv2.erode(a, np.ones((3, 3), np.uint8))  # buang halo tepi
    return rgb, a


def grade(img, lum_w=np.array([0.2126, 0.7152, 0.0722], np.float32)):
    lum = img @ lum_w
    sh = (1 - smoothstep(0.0, 0.6, lum))[..., None]
    hi = smoothstep(0.45, 1.0, lum)[..., None]
    img = img + sh * np.array([-0.07, 0.015, 0.06]) + hi * np.array([0.06, 0.02, -0.06])
    img = np.clip(img, 0, 1)
    img = img + 0.25 * (img - 0.5) * (1 - np.abs(2 * img - 1))
    return np.clip(img, 0, 1).astype(np.float32)


# ---------------------------------------------------------------- komposisi

def main():
    bg = grade(background())
    h, w = H * S, W * S
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32) / S

    # cahaya matahari & suar anamorfik di ufuk kiri
    sun = (205, 520)
    d = np.hypot(xx - sun[0], (yy - sun[1]) * 1.7)
    bg = screen(bg, np.exp(-(d / 360) ** 2)[..., None] * 0.55,
                np.array([1.0, 0.62, 0.25], np.float32))
    dy = np.abs(yy - sun[1])
    streak = (np.exp(-(dy / 2.2) ** 2) + 0.3 * np.exp(-(dy / 10) ** 2)) * \
        np.exp(-np.abs(xx - sun[0]) / 300)
    bg = screen(bg, streak[..., None] * 0.8, np.array([1.0, 0.85, 0.65], np.float32))

    # subjek dengan cahaya pinggir (rim light) hangat dari arah matahari
    srgb, sa = subject_layer()
    srgb = grade(srgb)
    edge = np.clip(sa - cv2.GaussianBlur(sa, (0, 0), 6 * S), 0, 1)
    side = 1 - smoothstep(380, 760, xx)  # sisi kiri lebih terang
    rim = (edge * (0.35 + 0.65 * side) * 2.2)[..., None]
    srgb = screen(srgb, np.clip(rim, 0, 1), np.array([1.0, 0.7, 0.35], np.float32))
    # bayang lembut di belakang subjek supaya tidak "terpampang"
    shadow = cv2.GaussianBlur(sa, (0, 0), 28 * S)[..., None]
    img = bg * (1 - 0.45 * shadow)
    img = img * (1 - sa[..., None]) + srgb * sa[..., None]

    # gelap di atas (ruang tagline) dan bawah (ruang judul)
    top = (1 - smoothstep(0, 260, yy)) * 0.78
    bot = smoothstep(620, 900, yy)
    dark = np.array([0.015, 0.03, 0.045], np.float32)
    img = img * (1 - top[..., None]) + dark * top[..., None]
    img = img * (1 - bot[..., None]) + dark * bot[..., None]

    # vignet
    v = np.hypot((xx - W / 2) / (W * 0.6), (yy - H * 0.45) / (H * 0.65))
    img = img * (1 - 0.5 * smoothstep(0.55, 1.3, v))[..., None]

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
    arr = arr + (grain * (0.05 * (1 - np.abs(2 * lum - 1)) + 0.012))[..., None]
    out = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
    out.save(HERE / "Pusat_Data_AI_wayang_2x.jpg", quality=94, subsampling=0)
    out.resize((W, H), Image.LANCZOS).save(HERE / "Pusat_Data_AI_wayang.jpg",
                                           quality=95, subsampling=0)


# ---------------------------------------------------------------- tipografi

def typography(canvas):
    size = canvas.size
    base = np.asarray(canvas, np.float32) / 255
    small = font("Oswald[wght].ttf", 13, 300)
    star = font("Cinzel[wght].ttf", 30, 500)
    tag = font("CormorantGaramond[wght].ttf", 30, 500)

    # --- judul: TANJUNG / BIDARA / PUSAT DATA AI
    title = font("Cinzel[wght].ttf", 186, 700)
    over = font("Cinzel[wght].ttf", 34, 400)
    sub = font("Cinzel[wght].ttf", 46, 700)

    # judul emas: topeng -> kecerunan logam -> glow
    t_mask = text_mask(size, [((540, 1088), "BIDARA", title, 6)])
    a = np.asarray(t_mask, np.float32)[..., None] / 255
    g_top, g_bot = 930, 1092
    grad = vgrad(int((g_bot - g_top) * S), [(0, GOLD_TOP), (0.42, (255, 214, 140)),
                                             (0.5, GOLD_MID), (0.78, (196, 120, 46)),
                                             (1, GOLD_LOW)]) / 255
    col = np.zeros_like(base)
    col[:] = grad[0]
    col[int(g_top * S):int(g_top * S) + len(grad)] = grad[:, None, :]
    col[int(g_top * S) + len(grad):] = grad[-1]
    ga, gc = glow(t_mask, 22, (255, 140, 40), 0.55)
    base = screen(base, ga, gc)
    sh_a = np.asarray(t_mask.filter(ImageFilter.GaussianBlur(3 * S)), np.float32)[..., None] / 255
    base = base * (1 - 0.6 * sh_a)
    base = base * (1 - a) + col * a

    # teks lain dilukis terus
    canvas = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(canvas)
    draw_tracked(d, (540, 915), "TANJUNG", over, CREAM + (255,), 30)
    # PUSAT DATA AI dengan garis halus kiri & kanan
    wsub = draw_tracked(d, (540, 1162), "PUSAT DATA AI", sub, (245, 240, 232), 14)
    for sgn in (-1, 1):
        x0 = 540 + sgn * (wsub / 2 + 22)
        x1 = 540 + sgn * (wsub / 2 + 120)
        d.line([(x0 * S, 1146 * S), (x1 * S, 1146 * S)], fill=GOLD_MID, width=int(1.5 * S))

    # --- atas: "mempersembahkan" + bil. bintang + tagline
    draw_tracked(d, (540, 44), "MELAKA STREET TALK MEMPERSEMBAHKAN", small, GREY, 5.5)
    draw_tracked(d, (540, 88), "TOK RAUF", star, CREAM, 16)

    # tagline di ruang langit
    draw_tracked(d, (540, 156), "Internet dunia naik ke darat di pantai ini.", tag, CREAM, 1.2)
    draw_tracked(d, (540, 194), "Kini, otaknya pula dirancang di sini.", tag, (240, 190, 120), 1.2)

    # --- blok kredit (billing block) gaya wayang: label kecil, nama besar
    billing(d)

    # --- tarikh tayangan
    rel = font("Cinzel[wght].ttf", 26, 700)
    draw_tracked(d, (540, 1300), "AKAN DATANG", rel, GOLD_MID, 12)

    foot = font("Oswald[wght].ttf", 9.5, 300)
    draw_tracked(d, (540, 1333),
                 "FOTO: AKUUJANG / WIKIMEDIA COMMONS, CC BY-SA 4.0  ·  POTRET: UMNO ONLINE  ·  "
                 "SUAR & CAHAYA: GAMBARAN  ·  PUSAT DATA MASIH DIRANCANG",
                 foot, (110, 116, 126), 1.6)
    return canvas


def billing(d):
    """Blok kredit ala poster wayang: League Gothic sempit, campur saiz."""
    lab = font("LeagueGothic[wdth].ttf", 15, 75)
    big = font("LeagueGothic[wdth].ttf", 25, 75)
    lines = [
        [("MELAKA STREET TALK", big), ("MEMPERSEMBAHKAN", lab), ("SEBUAH KISAH", lab),
         ("TOK RAUF", big), ("BERDASARKAN LAPORAN", lab), ("MELAKA HARI INI", big),
         ("5.10.2026", big)],
        [("LOKASI", lab), ("MASJID TANAH", big), ("DENGAN", lab), ("KABEL DASAR LAUT", lab),
         ("SEA-ME-WE 5", big), ("DI", lab), ("PANTAI TANJUNG BIDARA", big)],
    ]
    col = (168, 172, 180)
    for i, line in enumerate(lines):
        y = 1218 + i * 30
        gap = 9
        widths = [tracked_width(t, f, 1.0) / S for t, f in line]
        total = sum(widths) + gap * (len(line) - 1)
        x = 540 - total / 2
        for (t, f), wd in zip(line, widths):
            draw_tracked(d, (x, y), t, f, col, 1.0, anchor="left")
            x += wd + gap


if __name__ == "__main__":
    main()

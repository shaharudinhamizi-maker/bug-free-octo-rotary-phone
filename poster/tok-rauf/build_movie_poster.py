"""Bina semula poster 'Pusat Data AI Tanjung Bidara' gaya poster wayang.

Guna: python3 build_movie_poster.py
Input : Pusat_Data_AI_asal.jpg (latar pantai, skala 1:1),
        subjek_mikrofon.png (potongan RGBA dari potret_mikrofon.jpg),
        subjek.png (potongan subjek lama, hanya untuk membersihkan latar)
Output: Pusat_Data_AI_wayang.jpg (1080x1350) + Pusat_Data_AI_wayang_2x.jpg

Wording hanya dari poster asal.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
W, H, S = 1080, 1350, 2  # kanvas asas, dirender pada skala S

SCENE_END = 880  # pemandangan asal berakhir di sini; bawahnya ruang judul
# Langit atas (y < SKY_ROWS) diregang ke bawah sebanyak SHIFT piksel supaya
# pemandangan turun sedikit dan ruang judul di bawah lebih seimbang.
SKY_ROWS, SHIFT = 200, 50
# Subjek baharu diletak di tempat subjek lama (dicari supaya menutup
# hampir seluruh subjek lama). Diterbalikkan supaya menghadap laut/matahari.
SUBJECT = dict(file="subjek_mikrofon.png", scale=1.5, pos=(-40, 224 + SHIFT), mirror=True)
SUN = (205, 520 + SHIFT)
NAVY_TOP, NAVY_BOT = (16, 32, 56), (8, 15, 28)

GOLD_MID = (232, 170, 82)
CREAM = (246, 240, 228)
GOLD = [(0, (255, 238, 196)), (0.45, (255, 212, 134)), (0.52, GOLD_MID),
        (0.8, (196, 118, 44)), (1, (160, 88, 30))]
SILVER = [(0, (255, 255, 255)), (0.5, (238, 240, 244)), (0.56, (200, 208, 218)),
          (1, (165, 175, 190))]
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
    """items: senarai (xy, text, font, track[, anchor]). Pulangkan topeng L."""
    m = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(m)
    for it in items:
        draw_tracked(d, it[0], it[1], it[2], 255, it[3], *(it[4:] or ["center"]))
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

def fill_sideways(img, mask, split):
    """Isi kawasan bertopeng secara mendatar dengan piksel bersih terdekat:
    dari kiri bagi x < split (laut/langit), dari kanan bagi x >= split."""
    out = img.astype(np.float32).copy()
    for y in np.where(mask.any(1))[0]:
        row = mask[y]
        xs = np.where(~row)[0]
        if len(xs) == 0:
            continue
        idx = np.where(row)[0]
        pos = np.searchsorted(xs, idx)
        left = xs[np.clip(pos - 1, 0, len(xs) - 1)]
        right = xs[np.clip(pos, 0, len(xs) - 1)]
        use_left = ((idx < split) & (pos > 0)) | (pos >= len(xs))
        out[y, idx] = out[y, np.where(use_left, left, right)]
    return out


def background():
    src = cv2.cvtColor(cv2.imread(str(HERE / "Pusat_Data_AI_asal.jpg")), cv2.COLOR_BGR2RGB)

    # 1. teks lama di atas: piksel yang jauh lebih terang daripada langit sekitar
    v = cv2.cvtColor(src, cv2.COLOR_RGB2HSV)[..., 2].astype(np.int16)
    med = cv2.medianBlur(v.astype(np.uint8), 21).astype(np.int16)
    band = np.zeros(v.shape, bool)
    band[30:160, 140:940] = True
    # teks lama krim/oren (V > 185) lebih terang daripada langit (V < 175);
    # pelepah kelapa gelap tidak tersentuh
    rr, bb = src[..., 0].astype(np.int16), src[..., 2].astype(np.int16)
    tmask = (band & ((v > 185) | ((rr - bb > 50) & (rr > 140)))).astype(np.uint8) * 255
    tmask = cv2.dilate(tmask, np.ones((5, 5), np.uint8))
    # titik cahaya "garis data" di atas laut (titik kecil jauh lebih terang)
    r, b = src[..., 0].astype(np.int16), src[..., 2].astype(np.int16)
    sea = np.zeros(v.shape, bool)
    sea[560:SCENE_END, :] = True
    dots = sea & (v > med + 40) & (b >= r)
    tmask |= cv2.dilate(dots.astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
    src = cv2.inpaint(src, tmask, 5, cv2.INPAINT_TELEA)

    # 2. subjek lama: diisi dari sisi (kebanyakannya ditutup subjek baharu)
    old = cv2.imread(str(HERE / "subjek.png"), cv2.IMREAD_UNCHANGED)[..., 3]
    om = np.zeros(v.shape, np.uint8)
    om[300:300 + old.shape[0], :old.shape[1]] = (old > 10) * 255
    om = cv2.dilate(om, np.ones((21, 21), np.uint8)) > 0
    filled = fill_sideways(src, om, split=560)
    soft = cv2.GaussianBlur(filled, (0, 0), 8)
    m = cv2.GaussianBlur(om.astype(np.float32), (0, 0), 4)[..., None]
    img = filled * (1 - m) + soft * m

    img = np.clip(img, 0, 255).astype(np.uint8)
    sky = cv2.resize(img[:SKY_ROWS], (img.shape[1], SKY_ROWS + SHIFT),
                     interpolation=cv2.INTER_CUBIC)
    img = np.vstack([sky, img[SKY_ROWS:H - SHIFT]])
    im = Image.fromarray(img).resize((W * S, H * S), Image.LANCZOS)
    im = im.filter(ImageFilter.GaussianBlur(0.9 * S))  # lembut sedikit, padan subjek
    arr = np.asarray(im, np.float32) / 255

    # 3. bawah pemandangan: biru laut dalam (bukan hitam) untuk ruang judul
    yy = np.arange(H * S, dtype=np.float32)[:, None, None] / S
    navy = np.array(NAVY_TOP, np.float32) / 255 + (
        np.array(NAVY_BOT, np.float32) - np.array(NAVY_TOP, np.float32)) / 255 * \
        np.clip((yy - SCENE_END - SHIFT) / (H - SCENE_END - SHIFT), 0, 1)
    end = SCENE_END + SHIFT
    t = smoothstep(end - 90, end - 5, yy)
    return arr * (1 - t) + navy * t


def subject_layer():
    sub = Image.open(HERE / SUBJECT["file"]).convert("RGBA")
    if SUBJECT["mirror"]:
        sub = ImageOps.mirror(sub)
    k = SUBJECT["scale"] * S
    sub = sub.resize((int(sub.width * k), int(sub.height * k)), Image.LANCZOS)
    layer = Image.new("RGBA", (W * S, H * S))
    px, py = SUBJECT["pos"]
    layer.alpha_composite(sub, (int(px * S), int(py * S)))
    arr = np.asarray(layer, np.float32) / 255
    rgb, a = arr[..., :3], arr[..., 3]

    # tepi bersih: buang sisa warna banner di piksel separa telus dengan
    # menggantikannya dengan warna dalaman subjek berhampiran
    core = (a > 0.98).astype(np.float32)
    num = cv2.GaussianBlur(rgb * core[..., None], (0, 0), 3 * S)
    den = cv2.GaussianBlur(core, (0, 0), 3 * S)[..., None]
    inner = num / np.maximum(den, 1e-4)
    dist = cv2.distanceTransform((a > 0.5).astype(np.uint8), cv2.DIST_L2, 5) / S
    edge = np.clip(1 - dist / 3.0, 0, 1)[..., None]  # 3 px terluar
    edge = np.maximum(edge, ((a > 0.01) & (a < 0.98)).astype(np.float32)[..., None])
    rgb = rgb * (1 - edge) + inner * edge
    # sisa banner putih di celah rambut: piksel dekat tepi yang jauh lebih
    # terang daripada warna dalaman sekitarnya
    num = cv2.GaussianBlur(rgb * core[..., None], (0, 0), 6 * S)
    den = cv2.GaussianBlur(core, (0, 0), 6 * S)[..., None]
    inner6 = num / np.maximum(den, 1e-4)
    spill = (dist < 10) & ((rgb @ LUM) > (inner6 @ LUM) + 0.12)
    w = cv2.GaussianBlur(spill.astype(np.float32), (0, 0), 0.8 * S)[..., None] * 0.9
    rgb = rgb * (1 - w) + inner6 * w
    # tajamkan sedikit (gambar sumber kecil, dibesarkan)
    blur = cv2.GaussianBlur(rgb, (0, 0), 1.4 * S)
    rgb = np.clip(rgb + 0.55 * (rgb - blur), 0, 1)
    a = cv2.erode(a, np.ones((2 * S, 2 * S), np.uint8))
    # licinkan kontur bergerigi (topeng asal resolusi rendah) + tepi lembut
    a = cv2.GaussianBlur(a, (0, 0), 2.0 * S)
    a = smoothstep(0.25, 0.75, a)
    a = cv2.GaussianBlur(a, (0, 0), 0.9 * S)

    # tepi bawah gambar dilebur ke ruang judul
    yy = np.arange(H * S, dtype=np.float32)[:, None] / S
    bottom = py + sub.height / S
    a = a * (1 - smoothstep(bottom - 70, bottom - 4, yy))
    return rgb, a


def match_subject(rgb, a, xx):
    """Padan warna subjek dengan cahaya senja: hangat dari kiri (matahari)."""
    rgb = rgb * np.array([1.03, 0.99, 0.94], np.float32)
    side = (1 - smoothstep(150, 750, xx))[..., None]
    rgb = screen(rgb, side * 0.10, (1.0, 0.72, 0.42))
    return np.clip(rgb, 0, 1)


# ---------------------------------------------------------------- komposisi

def main():
    bg = background()
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32) / S

    # cahaya matahari di ufuk kiri + suar mendatar halus
    d = np.hypot(xx - SUN[0], (yy - SUN[1]) * 1.7)
    bg = screen(bg, np.exp(-(d / 300) ** 2)[..., None] * 0.35, (1.0, 0.7, 0.35))
    dy = np.abs(yy - SUN[1])
    streak = np.exp(-(dy / 2.0) ** 2) * np.exp(-np.abs(xx - SUN[0]) / 260)
    bg = screen(bg, streak[..., None] * 0.6, (1.0, 0.88, 0.7))

    srgb, sa = subject_layer()
    srgb = match_subject(srgb, sa, xx)
    shadow = cv2.GaussianBlur(sa, (0, 0), 16 * S)[..., None]
    img = bg * (1 - 0.18 * shadow)
    img = img * (1 - sa[..., None]) + srgb * sa[..., None]

    img = typography(img)

    # grain filem halus
    grain = cv2.GaussianBlur(np.random.default_rng(11).normal(0, 1, (H * S, W * S))
                             .astype(np.float32), (0, 0), 0.6 * S)
    lum = np.clip(img, 0, 1) @ LUM
    img = img + (grain * (0.022 * (1 - np.abs(2 * lum - 1)) + 0.006))[..., None]
    out = to_img(img)
    out.save(HERE / "Pusat_Data_AI_wayang_2x.jpg", quality=94, subsampling=0)
    out.resize((W, H), Image.LANCZOS).save(HERE / "Pusat_Data_AI_wayang.jpg",
                                           quality=95, subsampling=0)


# ---------------------------------------------------------------- tipografi

def typography(base):
    # KISAH TOK RAUF: besar, TOK RAUF emas bercahaya
    k1 = font("Cinzel[wght].ttf", 48, 700)
    k2 = font("Cinzel[wght].ttf", 74, 900)
    w1 = tracked_width("KISAH", k1, 10) / S
    w2 = tracked_width("TOK RAUF", k2, 8) / S
    x = 540 - (w1 + 28 + w2) / 2
    base = metal(base, [((x + w1 / 2, 104), "KISAH", k1, 10)], 64, 104, SILVER, shadow=(5, 0.8))
    base = metal(base, [((x + w1 + 28 + w2 / 2, 104), "TOK RAUF", k2, 8)], 48, 106, GOLD,
                 (255, 130, 30), 14, 0.55, shadow=(5, 0.8))

    # judul: PUSAT DATA (perak) + AI (emas, lebih besar, bercahaya)
    t1 = font("Cinzel[wght].ttf", 96, 800)
    t2 = font("Cinzel[wght].ttf", 168, 900)
    wa = tracked_width("PUSAT DATA", t1, 6) / S
    wb = tracked_width("AI", t2, 6) / S
    gap = 26
    x0 = 540 - (wa + gap + wb) / 2
    base_y = 1150
    base = metal(base, [((x0 + wa / 2, base_y), "PUSAT DATA", t1, 6)], base_y - 70, base_y,
                 SILVER, (150, 190, 255), 16, 0.18, shadow=(6, 0.6))
    ai_x = x0 + wa + gap + wb / 2
    base = metal(base, [((ai_x, base_y), "AI", t2, 6)], base_y - 122, base_y, GOLD,
                 (255, 125, 25), 26, 0.75, shadow=(6, 0.6))
    # suar anamorfik halus merentas AI
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32) / S
    fy = base_y - 60
    fl = np.exp(-((yy - fy) / 1.6) ** 2) * np.exp(-np.abs(xx - ai_x) / 210)
    base = screen(base, fl[..., None] * 0.75, (1.0, 0.82, 0.55))

    tag = font("CormorantGaramond[wght].ttf", 34, 600)
    lab = font("Oswald[wght].ttf", 18, 500)
    sub = font("Cinzel[wght].ttf", 36, 700)
    foot = font("Oswald[wght].ttf", 10, 400)
    t_a, t_b = "Kabel internet dunia naik ke darat ", "di pantai ini."
    credit = "FOTO LATAR: AKUUJANG / WIKIMEDIA COMMONS, CC BY-SA 4.0  ·  PUSAT DATA MASIH DIRANCANG"

    base = drop_shadow(base, text_mask([((540, 162), t_a + t_b, tag, 1.0)]), 5, 0.85)
    canvas = to_img(base)
    d = ImageDraw.Draw(canvas)

    wa = tracked_width(t_a, tag, 1.0) / S
    wb = tracked_width(t_b, tag, 1.0) / S
    x = 540 - (wa + wb) / 2
    draw_tracked(d, (x, 162), t_a, tag, CREAM, 1.0, anchor="left")
    draw_tracked(d, (x + wa, 162), t_b, tag, (255, 190, 100), 1.0, anchor="left")

    draw_tracked(d, (540, 1012), "TOK RAUF UMUM  ·  DIRANCANG", lab, (240, 190, 120), 8)

    wsub = draw_tracked(d, (540, 1238), "TANJUNG BIDARA", sub, CREAM, 18)
    for sgn in (-1, 1):
        x0 = 540 + sgn * (wsub / 2 + 22)
        x1 = 540 + sgn * (wsub / 2 + 110)
        d.line([(x0 * S, 1226 * S), (x1 * S, 1226 * S)], fill=GOLD_MID, width=int(1.5 * S))

    draw_tracked(d, (540, 1330), credit, foot, (120, 130, 145), 1.8)
    return np.asarray(canvas, np.float32) / 255


if __name__ == "__main__":
    main()

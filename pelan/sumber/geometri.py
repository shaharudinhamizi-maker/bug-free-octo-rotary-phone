# -*- coding: utf-8 -*-
"""
Geometri rumah (sumber tunggal untuk pelan 2D dan model 3D).

Semua ukuran dalam KAKI.
  X  -> ke timur  (0 = tepi barat zon dapur & dobi)
  Y  -> ke utara  (0 = muka depan dinding hadapan rumah; anjung di Y -6..0)
  Z  -> ke atas   (0 = aras lantai bawah siap)

Dinding luar 9" (0.75'), dinding dalam 4½" (0.375'), dinding zon dapur 6" (0.5').
Disalin daripada lakaran asal pengguna dan dikemaskan supaya ukuran bilik
sepadan dengan label asal (lebih kurang beberapa inci).
"""

EXT, INT, SIDE = 0.75, 0.375, 0.5

# Ketinggian (kaki)
H_FLOOR1 = 10.5      # aras lantai bawah -> aras lantai atas
H_FLOOR2 = 10.0      # aras lantai atas  -> aras siling atas / alang bumbung
H_DOOR = 7.0
H_DOOR_MAIN = 7.5
SILL, HEAD = 3.0, 7.0

# --------------------------------------------------------------------------
# Dinding: (x0, x1, y0, y1, jenis)
# --------------------------------------------------------------------------
WALLS = [
    # rumah utama - luar
    (10.0, 35.0, 0.0, 0.75, 'ext'),        # hadapan (selatan)
    (10.0, 35.0, 29.25, 30.0, 'ext'),      # belakang (utara)
    (10.0, 10.75, 0.0, 30.0, 'ext'),       # barat
    (34.25, 35.0, 0.0, 30.0, 'ext'),       # timur
    # rumah utama - dalam
    (15.75, 16.125, 20.875, 29.25, 'int'),   # bilik air - timur
    (10.75, 16.125, 20.875, 21.25, 'int'),   # bilik air - selatan
    (14.25, 14.625, 16.0, 20.875, 'int'),    # stor - timur
    (10.75, 14.625, 16.0, 16.375, 'int'),    # stor - selatan
    (16.125, 20.125, 25.375, 25.75, 'int'),  # almari - hadapan
    (20.125, 20.5, 16.75, 29.25, 'int'),     # bilik tidur - barat
    (20.125, 34.25, 16.75, 17.125, 'int'),   # bilik tidur - selatan
    # zon dapur & dobi (sisi barat)
    (0.0, 0.5, 8.0, 30.0, 'side'),           # barat
    (0.0, 3.0, 29.5, 30.0, 'side'),          # belakang (kiri bukaan)
    (7.0, 10.0, 29.5, 30.0, 'side'),         # belakang (kanan bukaan)
    (7.0, 10.0, 24.0, 24.375, 'side'),       # dinding ceruk dobi
]

# --------------------------------------------------------------------------
# Bukaan: (x0, x1, y0, y1, jenis, aras_ambang, aras_atas)
#   jenis: 'win' tingkap, 'door' pintu
# Segi empat bukaan meliputi seluruh tebal dinding.
# --------------------------------------------------------------------------
OPENINGS = [
    # dinding hadapan
    (11.25, 15.75, 0.0, 0.75, 'win', SILL, HEAD),
    (16.75, 21.25, 0.0, 0.75, 'door', 0.0, H_DOOR_MAIN),     # pintu utama ibu-anak
    (23.75, 28.25, 0.0, 0.75, 'win', SILL, HEAD),
    (29.25, 33.75, 0.0, 0.75, 'win', SILL, HEAD),
    # dinding belakang
    (11.75, 14.75, 29.25, 30.0, 'win', 5.25, HEAD),          # tingkap tinggi bilik air
    (21.5, 24.5, 29.25, 30.0, 'win', SILL, HEAD),
    (30.75, 33.75, 29.25, 30.0, 'win', SILL, HEAD),
    # dinding barat rumah
    (10.0, 10.75, 1.25, 6.75, 'win', SILL, HEAD),
    (10.0, 10.75, 8.75, 14.75, 'door', 0.0, H_DOOR),         # pintu berkembar ke dapur
    (10.0, 10.75, 17.25, 19.75, 'door', 0.0, H_DOOR),        # pintu stor
    # dinding timur
    (34.25, 35.0, 1.25, 7.25, 'win', SILL, HEAD),
    (34.25, 35.0, 11.25, 14.25, 'win', SILL, HEAD),
    (34.25, 35.0, 18.25, 21.25, 'win', SILL, HEAD),
    (34.25, 35.0, 25.75, 28.75, 'win', SILL, HEAD),
    # dalaman
    (15.75, 16.125, 21.5, 24.0, 'door', 0.0, H_DOOR),        # bilik air
    (16.375, 19.875, 25.375, 25.75, 'door', 0.0, H_DOOR),    # almari (berkembar)
    (20.125, 20.5, 17.375, 20.375, 'door', 0.0, H_DOOR),     # bilik tidur
    # zon dapur - tingkap atas kabinet
    (0.0, 0.5, 8.75, 12.25, 'win', 3.75, HEAD),
    (0.0, 0.5, 17.75, 22.75, 'win', 3.75, HEAD),
    (0.0, 0.5, 23.75, 28.75, 'win', 3.75, HEAD),
]

# --------------------------------------------------------------------------
# Daun pintu untuk lukisan: (engsel_x, engsel_y, jejari, arah_daun, arah_tutup)
#   arah dalam darjah (0 = timur, 90 = utara, 180 = barat, 270 = selatan)
# --------------------------------------------------------------------------
DOOR_LEAVES = [
    (16.75, 0.0, 1.5, 270, 0),       # pintu utama - daun kecil (anak)
    (21.25, 0.0, 3.0, 270, 180),     # pintu utama - daun besar (ibu)
    (10.0, 14.75, 3.0, 180, 270),    # pintu berkembar ruang makan -> dapur
    (10.0, 8.75, 3.0, 180, 90),
    (10.0, 19.75, 2.5, 180, 270),    # pintu stor (buka ke luar)
    (15.75, 21.5, 2.5, 180, 90),     # pintu bilik air
    (16.375, 25.375, 1.75, 270, 0),  # almari berkembar
    (19.875, 25.375, 1.75, 270, 180),
    (20.5, 17.375, 3.0, 0, 90),      # pintu bilik tidur
]

# --------------------------------------------------------------------------
# Kawasan (lantai) : (x0, x1, y0, y1)
# --------------------------------------------------------------------------
HOUSE = (10.0, 35.0, 0.0, 30.0)
SIDE_ZONE = (0.0, 10.0, 0.0, 30.0)
PORCH = (0.0, 35.0, -6.0, 0.0)

ROOMS = {
    'tamu':    (22.81, 34.25, 0.75, 16.75),
    'makan':   (10.75, 22.31, 0.75, 16.0),
    'tidur':   (20.5, 34.25, 17.125, 29.25),
    'air':     (10.75, 15.75, 21.25, 29.25),
    'stor':    (10.75, 14.25, 16.375, 20.875),
    'almari':  (16.125, 20.125, 25.75, 29.25),
    'laluan':  (16.125, 20.125, 16.375, 25.375),
}

# Perabot / kelengkapan utama (segi empat x0, x1, y0, y1)
STAIR = (19.75, 25.5, 11.0, 16.75)
STAIR_SPLIT = 22.625
STAIR_LANDING_Y = 13.25
DIVIDER = (22.31, 22.81, 0.75, 8.0)        # sekatan kaca ruang makan / tamu
DINING_TABLE = (12.5, 15.5, 2.25, 7.25)
COFFEE_TABLE = (27.25, 30.25, 4.75, 6.75)
TV_CONSOLE = (26.5, 32.5, 15.25, 16.75)
BED = (25.0, 30.5, 22.25, 29.25)
WARDROBE = (20.5, 22.5, 21.5, 28.0)
NIGHTSTAND = (31.0, 32.75, 27.75, 29.25)
DRESSER = (32.75, 34.25, 22.0, 25.5)
DESK = (30.5, 34.25, 17.125, 19.0)
HALL_CABINET = (14.625, 16.125, 16.375, 20.875)
WASHER = (8.0, 10.0, 24.6, 26.75)
DRYER = (8.0, 10.0, 27.1, 29.25)
UTILITY_SINK = (8.0, 10.0, 21.0, 23.75)
SOFA_U = [(23.0, 0.75), (34.25, 0.75), (34.25, 7.25), (32.0, 7.25),
          (32.0, 3.25), (25.5, 3.25), (25.5, 8.0), (23.0, 8.0)]

# Dapur & dobi
COUNTER_N = (0.5, 2.5, 14.75, 29.5)          # kabinet sepanjang dinding barat (utara)
COUNTER_PEN = (2.5, 6.0, 14.75, 17.0)        # semenanjung kabinet
BAR = (0.5, 6.0, 12.75, 14.75)               # meja bar (permukaan kayu)
COUNTER_S = (0.5, 2.5, 8.0, 12.75)           # kabinet sepanjang dinding barat (selatan)
KSINK = (0.75, 2.3, 19.5, 22.5)              # sinki dua mangkuk
HOB = (0.75, 2.25, 9.4, 11.6)                # dapur gas 2 tungku
KTABLE = (4.75, 10.4, 1.0, 1.45)             # meja bujur: pusat x, y, jejari x, jejari y
KSTOOLS = [(4.75, 11.85), (4.75, 8.95)]
SIDE_NORTH_GAP = (3.0, 7.0)                  # bukaan ke belakang (tiada dinding)

# Ruang makan: kerusi (pusat x, y, arah sandar dalam darjah)
DINING_CHAIRS = [(11.85, 3.5, 180), (11.85, 6.0, 180), (16.15, 3.5, 0), (16.15, 6.0, 0),
                 (14.0, 1.55, 270), (14.0, 7.95, 90)]
DESK_CHAIR = (32.25, 19.9, 0.72)              # pusat x, y, jejari

# Bilik air
WC = (10.75, 13.0, 24.4, 25.9)
BASIN = (11.65, 22.6, 0.75)                   # pusat x, y, jejari
SHOWER_WALL = (10.75, 13.5, 26.875, 27.125)   # dinding separuh tinggi
SHOWER_HEAD = (11.6, 28.45)
FLOOR_TRAP = (13.0, 28.25)

# Landskap: (x, y, jejari, jenis)
PLANTS = [
    (16.6, 30.95, 0.85, 'shrub'), (19.2, 31.25, 1.25, 'palm'), (27.4, 30.95, 0.85, 'shrub'),
    (1.4, 2.6, 1.15, 'shrub'), (2.75, 1.1, 1.0, 'shrub'),          # batas tanaman sudut barat daya
    (8.5, 1.3, 1.15, 'bigpot'),                                    # pokok pasu besar
    (16.05, -0.65, 0.5, 'pot'), (21.95, -0.65, 0.5, 'pot'),        # pasu di kiri kanan pintu utama
    (33.55, 15.95, 0.6, 'pot'),                                    # pasu dalam ruang tamu
]
PLANTER_SW = (0.0, 0.0, 4.0)                  # batas suku bulatan: pusat x, y, jejari

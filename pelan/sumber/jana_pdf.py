#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Himpun pelan berwarna + render 3D ke dalam satu PDF pembentangan A3 landskap.

    python3 jana_pdf.py   -> ../Rumah_Kediaman_Pembentangan_A3.pdf
Perlu: ../Pelan_Lantai_Bawah_A3.jpg dan ../Render_3D_{Luar,Udara,Pelan}.jpg
"""
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))
CHROME = os.environ.get('CHROME', '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
PDF = os.path.join(OUT, 'Rumah_Kediaman_Pembentangan_A3.pdf')


def img(name):
    return 'file://' + os.path.join(OUT, name)


RENDERS = [
    ('Render_3D_Luar.jpg', 'PANDANGAN LUAR', 'EXTERIOR VIEW', 'A-102',
     'Pandangan hadapan dari sudut barat daya'),
    ('Render_3D_Udara.jpg', 'PANDANGAN UDARA', 'AERIAL VIEW', 'A-103',
     'Bumbung pelana zink & beranda keliling'),
    ('Render_3D_Pelan.jpg', 'PELAN LANTAI 3D', '3D FLOOR PLAN', 'A-104',
     'Keratan tanpa bumbung · susun atur dalaman'),
]

CSS = """
@page { size: 420mm 297mm; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; font-family: Inter, sans-serif; color: #1d1d1b; }
.page { width: 420mm; height: 297mm; position: relative; overflow: hidden; page-break-after: always; break-after: page; }
.page:last-child { page-break-after: auto; break-after: auto; }
.frame { position: absolute; left: 7mm; top: 7mm; right: 7mm; bottom: 7mm; border: 0.6mm solid #1d1d1b; }
.frame2 { position: absolute; left: 4.8mm; top: 4.8mm; right: 4.8mm; bottom: 4.8mm; border: 0.15mm solid #1d1d1b; }
.full { position: absolute; inset: 0; width: 420mm; height: 297mm; }

/* muka depan */
.cover-img { position: absolute; left: 7mm; top: 7mm; width: 283mm; height: 283mm; object-fit: cover; object-position: 38% 50%; }
.cover-panel { position: absolute; right: 7mm; top: 7mm; width: 123mm; height: 283mm; background: #22211f; color: #fff;
               padding: 16mm 12mm 12mm 12mm; display: flex; flex-direction: column; }
.kicker { font-size: 3.4mm; font-weight: 600; letter-spacing: 0.9mm; color: #c9b08a; }
.t1 { font-size: 9mm; font-weight: 300; letter-spacing: 0.4mm; margin-top: 8mm; line-height: 1; }
.t2 { font-size: 11.5mm; font-weight: 800; letter-spacing: 0.3mm; line-height: 1.05; margin-top: 2mm; }
.lead { font-size: 3.6mm; line-height: 1.5; color: #d8d3ca; margin-top: 7mm; }
.rule { height: 0.3mm; background: #55524c; margin: 9mm 0 7mm; }
.toc-h { font-size: 2.8mm; font-weight: 600; letter-spacing: 0.7mm; color: #9d978c; margin-bottom: 4mm; }
.toc { list-style: none; padding: 0; margin: 0; }
.toc li { display: flex; align-items: baseline; gap: 4mm; padding: 2.6mm 0; border-bottom: 0.2mm solid #3a3834; font-size: 3.7mm; }
.toc .no { font-weight: 700; color: #c9b08a; width: 16mm; flex: none; }
.toc .nm { font-weight: 600; }
.toc .en { margin-left: auto; font-size: 2.6mm; letter-spacing: 0.4mm; color: #9d978c; }
.facts { display: grid; grid-template-columns: 1fr 1fr; gap: 4mm 6mm; margin-top: auto; }
.facts div { font-size: 2.6mm; letter-spacing: 0.4mm; color: #9d978c; font-weight: 600; }
.facts b { display: block; font-size: 4.4mm; letter-spacing: 0; color: #fff; font-weight: 700; margin-top: 1mm; }

/* halaman render */
.render { position: absolute; left: 7mm; top: 7mm; width: 406mm; height: 270.67mm; object-fit: cover; }
.strip { position: absolute; left: 7mm; right: 7mm; bottom: 7mm; height: 12.33mm; background: #22211f; color: #fff;
         display: flex; align-items: center; padding: 0 8mm; gap: 7mm; }
.strip .ttl { font-size: 5.2mm; font-weight: 800; letter-spacing: 0.3mm; }
.strip .en { font-size: 2.7mm; font-weight: 500; letter-spacing: 0.6mm; color: #bdb8ae; }
.strip .cap { font-size: 3.1mm; color: #d8d3ca; }
.strip .meta { margin-left: auto; display: flex; gap: 9mm; }
.strip .meta div { font-size: 2.2mm; letter-spacing: 0.5mm; color: #9d978c; font-weight: 600; }
.strip .meta b { display: block; font-size: 3.4mm; color: #fff; letter-spacing: 0; font-weight: 700; }
.sep { width: 0.3mm; height: 6mm; background: #55524c; }
"""


def cover():
    toc = [('A-101', 'Pelan lantai bawah', 'GROUND FLOOR PLAN'),
           ('A-102', 'Pandangan luar', 'EXTERIOR VIEW'),
           ('A-103', 'Pandangan udara', 'AERIAL VIEW'),
           ('A-104', 'Pelan lantai 3D', '3D FLOOR PLAN')]
    items = ''.join(f'<li><span class="no">{no}</span><span class="nm">{nm}</span>'
                    f'<span class="en">{en}</span></li>' for no, nm, en in toc)
    return f"""
<section class="page">
  <img class="cover-img" src="{img('Render_3D_Luar.jpg')}">
  <div class="cover-panel">
    <div class="kicker">LUKISAN PERSEMBAHAN</div>
    <div class="t1">CADANGAN</div>
    <div class="t2">RUMAH<br>KEDIAMAN</div>
    <div class="lead">Rumah satu tingkat 25' × 30' dengan loteng di bawah bumbung pelana zink,
      dapur &amp; dobi di sisi, serta beranda bertiang kayu di sekeliling.</div>
    <div class="rule"></div>
    <div class="toc-h">KANDUNGAN</div>
    <ul class="toc">{items}</ul>
    <div class="facts">
      <div>KELUASAN KASAR<b>1,260 kp · 117 m²</b></div>
      <div>SKALA PELAN<b>1:50 @ A3</b></div>
      <div>BILIK<b>1 bilik tidur · 1 bilik air</b></div>
      <div>TARIKH<b>OKT 2026</b></div>
    </div>
  </div>
  <div class="frame"></div><div class="frame2"></div>
</section>"""


def plan_page():
    return f"""
<section class="page"><img class="full" src="{img('Pelan_Lantai_Bawah_A3.jpg')}"></section>"""


def render_page(fn, nm, en, no, cap):
    return f"""
<section class="page">
  <img class="render" src="{img(fn)}">
  <div class="strip">
    <div><div class="ttl">{nm}</div><div class="en">{en}</div></div>
    <div class="sep"></div>
    <div class="cap">{cap}</div>
    <div class="meta"><div>PROJEK<b>Cadangan Rumah Kediaman</b></div>
      <div>TARIKH<b>OKT 2026</b></div><div>NO. LUKISAN<b>{no}</b></div></div>
  </div>
  <div class="frame"></div><div class="frame2"></div>
</section>"""


def main():
    pages = [cover(), plan_page()] + [render_page(*r) for r in RENDERS]
    html = ('<!doctype html><html><head><meta charset="utf-8"><title>Cadangan Rumah Kediaman</title>'
            f'<style>{CSS}</style></head><body>' + ''.join(pages) + '</body></html>')
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'pembentangan.html')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write(html)
        subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
                        '--allow-file-access-from-files', '--virtual-time-budget=5000',
                        '--no-pdf-header-footer', f'--print-to-pdf={PDF}', 'file://' + src],
                       check=True, stderr=subprocess.DEVNULL)
    print(PDF, os.path.getsize(PDF))


if __name__ == '__main__':
    main()

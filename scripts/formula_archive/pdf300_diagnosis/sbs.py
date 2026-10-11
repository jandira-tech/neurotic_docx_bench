# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys, glob, os, io
from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from reportlab.pdfgen import canvas
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
pairs = sorted({os.path.basename(f).split(" — ")[0] for f in glob.glob(f"{src}/*.pdf")})
for pair in pairs:
    files = sorted(glob.glob(f"{src}/{pair} — *.pdf"))
    readers = [PdfReader(f) for f in files]
    labels = [os.path.basename(f).split(" — ")[1][:-4] for f in files]
    w0 = max(float(r.pages[0].mediabox.width) for r in readers)
    h0 = max(float(r.pages[0].mediabox.height) for r in readers)
    gap, head = 18, 30
    W, H = len(readers) * w0 + (len(readers) + 1) * gap, h0 + head + gap
    n = max(len(r.pages) for r in readers)
    wr = PdfWriter()
    for i in range(n):
        buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
        c.setFillGray(0.93); c.rect(0, 0, W, H, fill=1, stroke=0)
        c.setFillGray(0.1); c.setFont("Helvetica-Bold", 13)
        for k, lab in enumerate(labels):
            x = gap + k * (w0 + gap)
            c.drawString(x, H - 21, f"{lab}  ·  page {i+1}/{len(readers[k].pages)}")
            if i >= len(readers[k].pages):
                c.setFillGray(0.5); c.drawString(x + 20, H / 2, "(no page)"); c.setFillGray(0.1)
        c.save(); buf.seek(0)
        page = PageObject.create_blank_page(width=W, height=H)
        page.merge_page(PdfReader(buf).pages[0])
        for k, r in enumerate(readers):
            if i < len(r.pages):
                p = r.pages[i]; x = gap + k * (w0 + gap); y = H - head - float(p.mediabox.height)
                page.merge_transformed_page(p, Transformation().translate(x - float(p.mediabox.left), y - float(p.mediabox.bottom)))
        wr.add_page(page)
    dst = f"{out}/{pair} — side by side.pdf"
    with open(dst, "wb") as f: wr.write(f)
    print(n, "rows", dst)
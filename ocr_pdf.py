#!/usr/bin/env python3
"""
OCR the signal & communications PDF using easyocr.
Output: .scratch/signal-comm/batch_XXX_pN-M.md
Usage: python3 ocr_pdf.py [start_page] [end_page]
"""
import fitz
import easyocr
import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

PDF_PATH = '/Users/wenzhiyuan/Desktop/PDF合并.pdf'
OUT_DIR = Path('/Users/wenzhiyuan/Desktop/ff1/.scratch/signal-comm')
BATCH_SIZE = 20
DPI = 150

def preprocess(img):
    img = img.convert('L')
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.point(lambda x: 0 if x < 128 else 255)
    return img

def main():
    start_page = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end_page = int(sys.argv[2]) if len(sys.argv) > 2 else None
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(PDF_PATH)
    total = doc.page_count
    if end_page is None:
        end_page = total
    else:
        end_page = min(end_page, total)

    print(f"Total pages: {total}, processing pages {start_page+1}-{end_page}")
    print("Loading easyocr models...")
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    print("Ready.\n")

    batch_f = None
    t_start = time.time()

    for pg in range(start_page, end_page):
        if pg == start_page or pg % BATCH_SIZE == 0:
            if batch_f:
                batch_f.close()
            batch_num = pg // BATCH_SIZE
            batch_start = pg + 1
            batch_end = min((batch_num + 1) * BATCH_SIZE, end_page)
            fname = f"batch_{batch_num:03d}_p{batch_start}-{batch_end}.md"
            batch_f = open(OUT_DIR / fname, 'w', encoding='utf-8')
            batch_f.write(f"# 信号与通信原理 — 第 {batch_num + 1} 批\n\n")
            batch_f.write(f"页码: {batch_start}-{batch_end} / {total}\n\n---\n\n")
            print(f"[batch {batch_num:03d}] {fname}")

        t0 = time.time()
        page = doc[pg]
        pix = page.get_pixmap(dpi=DPI)
        img_path = f'/tmp/ocr_ez_{pg+1}.png'
        pix.save(img_path)

        img = Image.open(img_path)
        img = preprocess(img)
        img.save(img_path)

        result = reader.readtext(img_path, detail=0)
        text = '\n'.join(result)

        batch_f.write(f"## 第 {pg+1} 页\n\n")
        batch_f.write(text if text.strip() else "[无文字 / 图片页]")
        batch_f.write("\n\n---\n\n")

        try:
            os.remove(img_path)
        except OSError:
            pass

        elapsed = time.time() - t0
        pages_done = pg - start_page + 1
        remaining = end_page - pg - 1
        eta = (remaining * (time.time() - t_start) / pages_done / 60) if pages_done > 0 and remaining > 0 else 0
        print(f"  p{pg+1}/{end_page} — {elapsed:.1f}s | ETA: {eta:.0f}min", flush=True)

    if batch_f:
        batch_f.close()
    doc.close()
    total_elapsed = (time.time() - t_start) / 60
    print(f"\nDone! Processed {end_page - start_page} pages in {total_elapsed:.1f}min")

if __name__ == '__main__':
    main()

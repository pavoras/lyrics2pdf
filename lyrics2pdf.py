#!/usr/bin/env python3
"""lyrics2pdf: turn a plain-text lyric file into a clean, styled PDF.

Usage:
    python lyrics2pdf.py song.txt -t "Title" -a "Artist" [-o out.pdf] [--cols 2] [--leading PT]

Line spacing auto-fits: the largest spacing that keeps everything on ONE page.
Extra space goes above each line, for writing chords.

Input format:
    - Stanzas separated by blank lines.
    - Optional section tags on their own line: [Verse], [Chorus], [Bridge], [Outro] ...
    - Without tags, any stanza that appears more than once is styled as a chorus.

Requires: pip install reportlab
"""
import argparse
import re
from collections import Counter
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageTemplate,
                                FrameBreak, Paragraph, Spacer, Table, TableStyle)

TAG = re.compile(r"^\s*\[(.+?)\]\s*$")
ACCENT = colors.HexColor("#8B1E3F")
GREY = colors.HexColor("#666666")

FONT_SIZE = 11.5
S = {
    "title":  ParagraphStyle("title", fontName="Times-Bold", fontSize=24, leading=28,
                             alignment=TA_CENTER, spaceAfter=1.5 * mm),
    "artist": ParagraphStyle("artist", fontName="Times-Italic", fontSize=12, leading=15,
                             alignment=TA_CENTER, textColor=GREY),
    "label":  ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=7.5, leading=9,
                             textColor=ACCENT, spaceAfter=0.5 * mm),
}


def set_leading(lead: float):
    """Line style with `lead` pt per line; text sits at the bottom of each slot,
    so the extra space ends up ABOVE every lyric line (room for chords)."""
    for name, font in (("line", "Times-Roman"), ("chorus", "Times-Italic")):
        S[name] = ParagraphStyle(name, fontName=font, fontSize=FONT_SIZE,
                                 leading=FONT_SIZE * 1.2, spaceBefore=lead - FONT_SIZE * 1.2)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse(text: str):
    """Return list of (label | None, [lines])."""
    blocks, label, cur = [], None, []
    for raw in text.splitlines() + [""]:
        line = raw.rstrip()
        m = TAG.match(line)
        if m:
            if cur:
                blocks.append((label, cur)); cur = []
            label = m.group(1).strip()
        elif not line:
            if cur:
                blocks.append((label, cur)); cur, label = [], None
        else:
            cur.append(line)
    return blocks


def auto_label(blocks):
    """Label untagged blocks: repeated -> Chorus, else Verse n."""
    counts = Counter(tuple(b) for _, b in blocks)
    out, v = [], 0
    for label, lines in blocks:
        if label is None:
            if counts[tuple(lines)] > 1:
                label = "Chorus"
            else:
                v += 1
                label = f"Verse {v}"
        out.append((label, lines))
    return out


def stanza(label, lines):
    is_chorus = "chorus" in label.lower() or "refrain" in label.lower()
    body = [Paragraph(esc(l), S["chorus" if is_chorus else "line"]) for l in lines]
    if is_chorus:  # accent bar on the left; row padding carries the chord space
        body = [Paragraph(esc(l), ParagraphStyle("c0", parent=S["chorus"], spaceBefore=0))
                for l in lines]
        t = Table([[b] for b in body], colWidths=["100%"])
        t.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), S["line"].spaceBefore),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        body = [t]
    return KeepTogether([Paragraph(label.upper(), S["label"]), *body, Spacer(1, GAP)])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, str(doc.page))
    canvas.restoreState()


GAP = 4 * mm


def render(blocks, out, title, artist, cols, lead):
    """Build PDF at given leading; return page count."""
    set_leading(lead)
    m, gap = 15 * mm, 10 * mm
    w, h = A4[0] - 2 * m, A4[1] - 2 * m
    head_h = 22 * mm

    def frames(first):
        top = h - head_h if first else h
        cw = (w - gap * (cols - 1)) / cols
        fs = [Frame(m + i * (cw + gap), m, cw, top, id=f"c{i}",
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
              for i in range(cols)]
        if first:
            fs.insert(0, Frame(m, m + top, w, head_h, id="head", leftPadding=0, rightPadding=0,
                                topPadding=0, bottomPadding=0))
        return fs

    doc = BaseDocTemplate(out, pagesize=A4, title=title, author=artist)
    doc.addPageTemplates([
        PageTemplate("first", frames(True), onPage=footer, autoNextPageTemplate="rest"),
        PageTemplate("rest", frames(False), onPage=footer),
    ])
    story = [Paragraph(esc(title), S["title"])]
    if artist:
        story.append(Paragraph(esc(artist), S["artist"]))
    story.append(FrameBreak())
    story += [stanza(l, b) for l, b in blocks]
    doc.build(story)
    return doc.page


def build(src: Path, out: Path, title: str, artist: str, cols: int, lead: float | None):
    blocks = auto_label(parse(src.read_text(encoding="utf-8")))
    if lead is None:  # binary search: largest leading that fits on one page
        lo, hi = FONT_SIZE * 1.2, 80.0
        if render(blocks, BytesIO(), title, artist, cols, lo) > 1:
            print("warning: does not fit on one page even at minimum spacing"
                  + ("" if cols == 2 else " - try --cols 2"))
            lead = lo
        else:
            for _ in range(20):
                mid = (lo + hi) / 2
                if render(blocks, BytesIO(), title, artist, cols, mid) == 1:
                    lo = mid
                else:
                    hi = mid
            lead = lo
    pages = render(blocks, str(out), title, artist, cols, lead)
    print(f"wrote {out}  ({len(blocks)} stanzas, line spacing {lead:.1f} pt "
          f"= {lead / FONT_SIZE:.1f}x font size, {pages} page(s))")


def main():
    p = argparse.ArgumentParser(
        prog="lyrics2pdf",
        description="Turn a plain-text lyric file into a styled one-page A4 PDF, "
                    "with space above every line for chords.",
        epilog="Stanzas are separated by blank lines; optional [Verse]/[Chorus]/... tags "
               "go on their own line. Untagged stanzas that repeat become choruses.")
    p.add_argument("src", type=Path, help="lyrics file (UTF-8 plain text)")
    p.add_argument("-t", "--title", default=None,
                   help="song title (default: derived from the file name)")
    p.add_argument("-a", "--artist", default="", help="artist line under the title")
    p.add_argument("-o", "--out", type=Path, default=None,
                   help="output PDF (default: SRC with .pdf extension)")
    p.add_argument("--cols", type=int, default=1, choices=[1, 2],
                   help="number of columns (default: 1)")
    p.add_argument("--leading", type=float, default=None,
                   help="fixed line spacing in pt (default: auto-fit to one page)")
    a = p.parse_args()
    build(a.src, a.out or a.src.with_suffix(".pdf"),
          a.title or a.src.stem.replace("_", " ").title(), a.artist, a.cols, a.leading)


if __name__ == "__main__":
    main()

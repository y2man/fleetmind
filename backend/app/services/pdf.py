"""A small, dependency-free PDF writer for text and tables (A4, Helvetica).

It exists so exports work without extra packages or system libraries. It handles what the
reports need: a title, headings, wrapped paragraphs, tables that continue across pages, and a
page footer. Text is encoded as Windows-1252; characters outside it print as "?".
Widths are estimated from per-class averages of Helvetica metrics, so long text is wrapped or
shortened conservatively rather than measured exactly.
"""
from __future__ import annotations

import textwrap
from datetime import datetime

PAGE_W, PAGE_H = 595.28, 841.89
MARGIN = 48.0
BOTTOM = 56.0  # keep clear of the footer


def _esc(s: str) -> bytes:
    b = s.encode("cp1252", errors="replace")
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def text_width(s: str, size: float, bold: bool = False) -> float:
    total = 0.0
    for ch in s:
        if ch.isdigit():
            w = 0.556
        elif ch == " ":
            w = 0.278
        elif ch in ".,:;|!'":
            w = 0.278
        elif ch in "il1jtfI()[]":
            w = 0.26 if ch in "ilj" else 0.33
        elif ch in "mwMW":
            w = 0.83
        elif ch.isupper():
            w = 0.69
        else:
            w = 0.556 if ch in "-_/%" else 0.53
        total += w
    return total * size * (1.06 if bold else 1.0)


def fit(s: str, width: float, size: float, bold: bool = False) -> str:
    """Shorten s with an ellipsis so it fits in width."""
    if text_width(s, size, bold) <= width:
        return s
    while s and text_width(s + "…", size, bold) > width:
        s = s[:-1]
    return s.rstrip() + "…"


class Pdf:
    def __init__(self, title: str, footer: str = "FleetMind") -> None:
        self.title, self.footer = title, footer
        self.pages: list[list[bytes]] = []
        self.y = 0.0
        self._new_page()

    # ---------------------------------------------------------------- layout
    def _new_page(self) -> None:
        self.pages.append([])
        self.y = PAGE_H - MARGIN

    def _ensure(self, height: float) -> None:
        if self.y - height < BOTTOM:
            self._new_page()

    def _put(self, x: float, y: float, s: str, size: float, bold: bool = False) -> None:
        font = "F2" if bold else "F1"
        self.pages[-1].append(b"BT /%b %.1f Tf %.2f %.2f Td (" % (font.encode(), size, x, y) + _esc(s) + b") Tj ET")

    def _rule(self, x1: float, x2: float, y: float, gray: float = 0.75) -> None:
        self.pages[-1].append(b"%.2f G 0.6 w %.2f %.2f m %.2f %.2f l S 0 G" % (gray, x1, y, x2, y))

    def title_block(self, title: str, subtitle: str | None = None) -> None:
        self._put(MARGIN, self.y - 20, title, 20, True)
        self.y -= 28
        if subtitle:
            self._put(MARGIN, self.y - 10, subtitle, 10)
            self.y -= 16
        self._rule(MARGIN, PAGE_W - MARGIN, self.y - 4)
        self.y -= 16

    def heading(self, s: str) -> None:
        self._ensure(40)
        self.y -= 10
        self._put(MARGIN, self.y - 12, s, 13, True)
        self.y -= 22

    def paragraph(self, s: str, size: float = 10, bold: bool = False) -> None:
        cols = max(20, int((PAGE_W - 2 * MARGIN) / (size * 0.53 * (1.06 if bold else 1))))
        for line in textwrap.wrap(s, cols) or [""]:
            self._ensure(size + 5)
            self._put(MARGIN, self.y - size, line, size, bold)
            self.y -= size + 4
        self.y -= 3

    def bullets(self, items: list[str], size: float = 9.5) -> None:
        cols = max(20, int((PAGE_W - 2 * MARGIN - 14) / (size * 0.53)))
        for it in items:
            for n, line in enumerate(textwrap.wrap(it, cols) or [""]):
                self._ensure(size + 5)
                if n == 0:
                    self._put(MARGIN + 2, self.y - size, "-", size)
                self._put(MARGIN + 14, self.y - size, line, size)
                self.y -= size + 3
        self.y -= 3

    def table(self, headers: list[str], rows: list[list[str]], widths: list[float], align: list[str] | None = None, size: float = 8.5) -> None:
        """widths are relative weights. align is one "l" or "r" per column."""
        usable = PAGE_W - 2 * MARGIN
        total = sum(widths)
        cw = [usable * w / total for w in widths]
        xs = [MARGIN + sum(cw[:i]) for i in range(len(cw))]
        align = align or ["l"] * len(headers)
        pad, row_h = 4.0, size + 7

        def draw(cells: list[str], bold: bool) -> None:
            for i, c in enumerate(cells):
                c = fit(str(c), cw[i] - 2 * pad, size, bold)
                x = xs[i] + pad if align[i] == "l" else xs[i] + cw[i] - pad - text_width(c, size, bold)
                self._put(x, self.y - size - 2, c, size, bold)

        def header() -> None:
            draw(headers, True)
            self.y -= row_h
            self._rule(MARGIN, PAGE_W - MARGIN, self.y + 2, 0.4)

        self._ensure(row_h * 3)
        header()
        if not rows:
            self._put(MARGIN + pad, self.y - size - 2, "No data in this range.", size)
            self.y -= row_h
        for r in rows:
            if self.y - row_h < BOTTOM:
                self._new_page()
                header()
            draw(r, False)
            self.y -= row_h
        self.y -= 6

    # ---------------------------------------------------------------- output
    def render(self) -> bytes:
        n = len(self.pages)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        contents: list[bytes] = []
        for i, ops in enumerate(self.pages, 1):
            footer = f"{self.footer}  |  generated {stamp}  |  page {i} of {n}"
            ops = ops + [b"BT /F1 8 Tf 0.4 g %.2f 30 Td (" % MARGIN + _esc(footer) + b") Tj ET 0 g"]
            contents.append(b"\n".join(ops))

        objs: list[bytes] = [b"", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
                             b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"]
        kids = []
        for i, c in enumerate(contents):
            page_id, content_id = 5 + 2 * i, 6 + 2 * i
            kids.append(b"%d 0 R" % page_id)
            objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % (PAGE_W, PAGE_H, content_id))
            objs.append(b"<< /Length %d >>\nstream\n" % len(c) + c + b"\nendstream")
        objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objs[1] = b"<< /Type /Pages /Kids [" + b" ".join(kids) + b"] /Count %d >>" % n
        info = b"<< /Title (" + _esc(self.title) + b") /Producer (FleetMind) >>"
        objs.append(info)

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, o in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, len(objs), xref)
        return bytes(out)

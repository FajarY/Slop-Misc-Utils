"""Draw the app icon (assets/icon.ico) so it can be regenerated without design tools."""

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (229, 72, 77)
WHITE = (255, 255, 255)
OUT = Path(__file__).resolve().parents[1] / "assets" / "icon.ico"


def draw(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 24  # design on the same 24-unit grid as the UI icons
    d.rounded_rectangle((0.5 * s, 0.5 * s, 23.5 * s, 23.5 * s), radius=5.5 * s, fill=ACCENT)

    # Page with a folded corner
    w = 1.6 * s
    left, top, right, bottom, fold = 6.5 * s, 4.5 * s, 17.5 * s, 19.5 * s, 4 * s
    outline = [(left, top), (right - fold, top), (right, top + fold), (right, bottom), (left, bottom)]
    d.polygon(outline, outline=WHITE, width=round(w))
    d.line([(right - fold, top), (right - fold, top + fold), (right, top + fold)], fill=WHITE,
           width=round(w), joint="curve")
    for y, x2 in ((12.5, 14.5), (15.5, 12.5)):
        d.line([(9 * s, y * s), (x2 * s, y * s)], fill=WHITE, width=round(w))
        for x in (9 * s, x2 * s):  # round caps
            d.ellipse((x - w / 2, y * s - w / 2, x + w / 2, y * s + w / 2), fill=WHITE)
    return img


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    draw().save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {OUT}")

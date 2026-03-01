import cv2
import tkinter as tk
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

# The sacred string — never mutated
CHARS = "I LOVE U "

# ── tunables ──────────────────────────────────────────────────────────────────
COLS       = 80
FONT_SIZE  = 20
BG         = (0, 0, 0)
BASE_COLOR = (255, 60, 180)   # pink
UPDATE_MS  = 25
# ──────────────────────────────────────────────────────────────────────────────


def _find_font(size):
    """Try to load a monospace font, fall back to PIL default."""
    candidates = [
        "cour.ttf", "Courier New.ttf", "CourierNew.ttf",
        "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


class AsciiCam:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("❤ ASCII Love Cam ❤")
        self.root.configure(bg="black")

        self.label = tk.Label(root, bg="black", bd=0)
        self.label.pack(fill="both", expand=True)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.label.config(text="Could not open camera.", fg="white")
            return

        self._font        = _find_font(FONT_SIZE)
        self._ready       = False
        self._tk_img      = None
        self._offset      = 0

        # Pre-render all 9 chars as small RGBA patches once — reuse every frame
        self._char_patches = {}   # char → np array (H, W, 4) white text on transparent

        self.root.after(100, self._init)

    def _init(self):
        ww = self.label.winfo_width()
        wh = self.label.winfo_height()
        if ww < 10 or wh < 10:
            self.root.after(100, self._init)
            return

        # Use font metrics for proper line height (no clipping, no gaps)
        ascent, descent = self._font.getmetrics()
        self._ch = ascent + descent          # full cell height
        # Width: measure a typical char
        tmp = Image.new("RGB", (200, 200))
        bb  = ImageDraw.Draw(tmp).textbbox((0, 0), "W", font=self._font)
        self._cw = bb[2] - bb[0]

        self._cols = max(1, ww // self._cw)
        self._rows = max(1, wh // self._ch)
        self._img_w = self._cols * self._cw
        self._img_h = self._rows * self._ch

        # Pre-render each unique char as a white-on-black patch
        # Draw at (0, -bb[1]) to cancel any top offset PIL adds, filling the cell cleanly
        for ch in set(CHARS):
            patch = Image.new("L", (self._cw, self._ch), 0)
            bb    = ImageDraw.Draw(patch).textbbox((0, 0), ch, font=self._font)
            y_off = -bb[1]   # shift up so glyph starts at pixel 0
            ImageDraw.Draw(patch).text((0, y_off), ch, fill=255, font=self._font)
            self._char_patches[ch] = np.array(patch, dtype=np.float32) / 255.0

        self._ready = True
        self._update()

    def _update(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            self._render(frame)
        self.root.after(UPDATE_MS, self._update)

    def _render(self, frame):
        if not self._ready:
            return

        rows, cols = self._rows, self._cols
        cw, ch     = self._cw, self._ch
        n_chars    = len(CHARS)

        # Resize + grayscale
        small = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0  # (rows, cols)

        # Build RGB output image
        out = np.zeros((self._img_h, self._img_w, 3), dtype=np.uint8)

        for r in range(rows):
            off      = self._offset
            row_lum  = gray[r]
            y0, y1   = r * ch, (r + 1) * ch

            for c in range(cols):
                ch_char = CHARS[(c - off) % n_chars]
                patch   = self._char_patches[ch_char]
                x0, x1  = c * cw, (c + 1) * cw
                lum     = row_lum[c]

                out[y0:y1, x0:x1, 0] = (patch * BASE_COLOR[0] * lum).astype(np.uint8)
                out[y0:y1, x0:x1, 1] = (patch * BASE_COLOR[1] * lum).astype(np.uint8)
                out[y0:y1, x0:x1, 2] = (patch * BASE_COLOR[2] * lum).astype(np.uint8)

        img     = Image.fromarray(out, "RGB")
        tk_img  = ImageTk.PhotoImage(img)
        self.label.config(image=tk_img)
        self._tk_img = tk_img   # keep reference
        self._offset = (self._offset + 1) % n_chars

    def destroy(self):
        if self.cap.isOpened():
            self.cap.release()


def main():
    root = tk.Tk()
    root.geometry("1000x560")
    app  = AsciiCam(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.destroy(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
"""
Prepare the portrait photo for clean ASCII conversion:
  1. remove the background (rembg) so the subject is isolated
  2. bilateral-smooth away texture/noise while keeping edges sharp
  3. stretch tones so skin lands near white and hair/lines stay dark
  4. darken the line work (difference-of-gaussians ridges)
  5. composite onto white and crop square around the subject

Output: grayscale prepped image, consumed by make_ascii_svg.py.

    python scripts/prep_photo.py [input] [output]
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import remove

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "..", "images", "Cinematic Coder Portrait with Blue Glow.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    HERE, "..", "images", "source-prepped.png")

LINE_WEIGHT = 0.6     # how hard drawn lines are pushed toward black

# 1. cut out the subject
cut = remove(Image.open(INP).convert("RGBA"))
rgb = np.array(cut.convert("RGB"))
alpha = np.array(cut.split()[-1])                 # 0 = background
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

# 2. smooth texture, keep edges
smooth = gray
for _ in range(3):
    smooth = cv2.bilateralFilter(smooth, 9, 40, 9)

# 3. tone stretch over the subject only
lo, hi = np.percentile(smooth[alpha > 128], [2, 92])
tone = np.clip((smooth.astype(np.float32) - lo) / (hi - lo), 0, 1)

# 4. dark-on-light ridges -> darken
fine = cv2.GaussianBlur(smooth, (0, 0), 1.5).astype(np.float32)
coarse = cv2.GaussianBlur(smooth, (0, 0), 6).astype(np.float32)
lines = np.clip((coarse - fine) / 40.0, 0, 1)
out = np.clip(tone - LINE_WEIGHT * lines, 0, 1) * 255

# 5. paste onto white (feathered a hair to avoid a halo), then a tight
# square crop around the face so the person fills the frame (a full-body
# crop leaves the face tiny and dark clothing dominates the art)
mask = cv2.GaussianBlur(alpha.astype(np.float32) / 255.0, (0, 0), 1.0)
out = out * mask + 255.0 * (1.0 - mask)

side = None
cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6,
                                 minSize=(80, 80))
if len(faces):
    fx, fy, fw, fh = max(faces, key=lambda b: b[2] * b[3])
    side = min(int(max(fw, fh) * 1.9), out.shape[0], out.shape[1])
    cx = int(fx + fw / 2)
    cy = int(fy + fh / 2 + side * 0.06)  # slight bias down to keep chin/shoulders
    cx = min(max(cx, side // 2), out.shape[1] - side // 2)
    cy = min(max(cy, side // 2), out.shape[0] - side // 2)
    print(f"face at {(fx, fy, fw, fh)}, tight crop side {side}")
    x0, y0 = cx - side // 2, cy - side // 2
    canvas = out[y0:y0 + side, x0:x0 + side].astype(np.uint8)
else:  # fallback: whole subject (original behavior)
    print("no face found, falling back to full-subject crop")
    ys, xs = np.where(alpha > 20)
    side = max(xs.max() - xs.min(), ys.max() - ys.min()) + 60
    cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
    canvas = np.full((side, side), 255, np.uint8)
    x0, y0 = cx - side // 2, cy - side // 2
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, out.shape[1]), min(y0 + side, out.shape[0])
    canvas[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = out[sy0:sy1, sx0:sx1].astype(np.uint8)

Image.fromarray(canvas, mode="L").save(OUT)
print("wrote", OUT, canvas.shape)

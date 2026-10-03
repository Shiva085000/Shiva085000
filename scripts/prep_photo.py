"""Prepare a portrait photo for ASCII conversion.

1. Isolate the subject: use the photo's alpha channel if it has one, else rembg
   if installed, else key out a flat studio/passport backdrop sampled from the corners.
2. Boost local contrast with CLAHE and sharpen so a flatly lit face gets real
   highlights and shadows.
3. Flatten onto pure white so the background maps to the blank end of the ramp.

Usage:
    python scripts/prep_photo.py source-photo.jpg [--crop 0.78] [--out source-prepped.png]
"""

import argparse

import cv2
import numpy as np
from PIL import Image, ImageFilter


def subject_mask(img: Image.Image) -> np.ndarray:
    """Return a 0..1 float mask where 1 is the subject."""
    if img.mode == "RGBA":
        alpha = np.asarray(img)[..., 3]
        if alpha.min() < 250:
            return alpha.astype(np.float32) / 255.0

    try:
        from rembg import remove  # optional, heavy dependency

        cut = remove(img.convert("RGB"))
        return np.asarray(cut)[..., 3].astype(np.float32) / 255.0
    except ImportError:
        pass

    # Flat backdrop: distance from the average corner colour.
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    k = max(8, min(rgb.shape[:2]) // 20)
    corners = np.concatenate(
        [rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3)]
    )
    bg = corners.mean(0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(-1))
    mask = np.clip((dist - 50) / 60, 0, 1)
    m = Image.fromarray((mask * 255).astype(np.uint8))
    m = m.filter(ImageFilter.MedianFilter(5)).filter(ImageFilter.MinFilter(3))
    m = m.filter(ImageFilter.GaussianBlur(1.0))
    return np.asarray(m).astype(np.float32) / 255.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--crop", type=float, default=0.78, help="keep this fraction of the height, from the top")
    ap.add_argument("--out", default="source-prepped.png")
    args = ap.parse_args()

    img = Image.open(args.photo)
    img = img.convert("RGBA") if img.mode in ("RGBA", "LA", "P") else img.convert("RGB")
    w, h = img.size
    img = img.crop((0, 0, w, int(h * args.crop)))

    mask = subject_mask(img)
    gray = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)

    gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6)).apply(gray)
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    gray = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)

    flat = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
    Image.fromarray(np.clip(flat, 0, 255).astype(np.uint8), "L").save(args.out)
    print(f"wrote {args.out} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()

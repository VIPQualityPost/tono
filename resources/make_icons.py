#!/usr/bin/env python3
"""
Generate icon files from an SVG source.

Workflow:
  SVG → 1024×1024 PNG (master, saved as icon_1024.png)
       → scaled PNGs: 512, 256, 128, 64, 32, 16
       → resources/icon.icns  (macOS, via iconutil)
       → resources/icon.ico   (Windows, via Pillow)

Usage:
    python resources/make_icons.py path/to/icon.svg

Requires:
    pip install pillow
    brew install librsvg      # provides rsvg-convert (SVG → PNG)
    macOS: iconutil           # pre-installed
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")


RESOURCES = Path(__file__).resolve().parent

# Sizes derived from the 1024 master. 16 is added for the .icns iconset.
SCALED_SIZES = [512, 256, 128, 64, 32, 16]

# macOS iconset: filename → source pixel size
ICONSET_MAP = {
    "icon_16x16.png":      16,
    "icon_16x16@2x.png":   32,
    "icon_32x32.png":      32,
    "icon_32x32@2x.png":   64,
    "icon_128x128.png":    128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png":    256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png":    512,
    "icon_512x512@2x.png": 1024,
}

# Sizes embedded in the .ico file (Windows; standard ICO max is 256)
ICO_SIZES = [256, 128, 64, 32, 16]


def find_rsvg_convert() -> str | None:
    if path := shutil.which("rsvg-convert"):
        return path
    # Homebrew puts it here even when not on PATH
    for prefix in ("/opt/homebrew", "/usr/local"):
        candidate = Path(prefix) / "bin" / "rsvg-convert"
        if candidate.exists():
            return str(candidate)
    return None


def svg_to_png(rsvg: str, svg_path: Path, out_path: Path, size: int) -> None:
    subprocess.run(
        [rsvg, "-w", str(size), "-h", str(size), str(svg_path), "-o", str(out_path)],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate .icns and .ico from an SVG.")
    parser.add_argument("svg", type=Path, help="Source SVG file")
    args = parser.parse_args()

    svg_path = args.svg.resolve()
    if not svg_path.exists():
        sys.exit(f"SVG not found: {svg_path}")

    rsvg = find_rsvg_convert()
    if rsvg is None:
        sys.exit(
            "rsvg-convert not found.\n"
            "Install it with:  brew install librsvg"
        )

    RESOURCES.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as _tmp:
        tmp = Path(_tmp)

        # ── 1. Render SVG → 1024×1024 master PNG ──────────────────────
        master = tmp / "icon_1024.png"
        print("Rendering SVG → 1024×1024 PNG…")
        svg_to_png(rsvg, svg_path, master, 1024)
        shutil.copy(master, RESOURCES / "icon_1024.png")
        print("  saved  icon_1024.png")

        # ── 2. Scale down to all needed sizes ─────────────────────────
        print("Scaling…")
        pngs: dict[int, Path] = {1024: master}
        with Image.open(master) as base:
            for size in SCALED_SIZES:
                out = tmp / f"icon_{size}.png"
                base.resize((size, size), Image.LANCZOS).save(out)
                pngs[size] = out
                print(f"  {size:>4}×{size}")

        # ── 3. Build .icns (macOS) ─────────────────────────────────────
        icns_out = RESOURCES / "icon.icns"
        if shutil.which("iconutil"):
            iconset = tmp / "icon.iconset"
            iconset.mkdir()
            for filename, size in ICONSET_MAP.items():
                shutil.copy(pngs[size], iconset / filename)
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_out)],
                check=True,
            )
            print("  saved  icon.icns")
        else:
            print("  iconutil not found — skipping icon.icns (run on macOS to generate it)")

        # ── 4. Build .ico (Windows) ────────────────────────────────────
        ico_out = RESOURCES / "icon.ico"
        images = [Image.open(pngs[s]).convert("RGBA") for s in ICO_SIZES]
        images[0].save(
            ico_out,
            format="ICO",
            sizes=[(s, s) for s in ICO_SIZES],
            append_images=images[1:],
        )
        print("  saved  icon.ico")

    print("Done.")


if __name__ == "__main__":
    main()

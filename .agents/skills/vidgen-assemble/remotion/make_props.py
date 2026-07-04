#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_props.py — sinh props.json cho Remotion overlay từ project.json + final.mp4 + BRAND PRESET.

Engine GENERIC: mọi giá trị brand (màu, wordmark, url, template, asset) đến từ preset
`assets/brands/<tên>/brand.json` (qua --brand-config). Không hardcode brand nào.

Chuẩn bị cho `npx remotion render VidgenOverlay out.mp4 --props=props.json`:
  1. Đo duration + kích thước bản NỘI DUNG (ffprobe) → contentDurationInFrames.
  2. End-card CỘNG THÊM ở cuối → durationInFrames = content + endcard.
  3. Nạp brand.json → copy asset preset (logo_lockup/mark/hero) + font + bg vào public/.
  4. (Tùy chọn) copy nốt chuông (--sonic) + lời CTA (--cta-voice).
  5. Ghi props.json (màu/template/wordmark/url từ preset; tagline biến thiên theo phẩm chất).

Thường được gọi qua apply_brand.py. Chạy tay:
  python make_props.py --project ../../../projects/<tên> \
    --brand-config ../../../assets/brands/<tên>/brand.json --endcard-sec 3
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]  # remotion → vidgen-assemble → skills → .agents → <repo>
FONT_SRC = HERE.parent / "assets" / "fonts" / "BeVietnamPro-Bold.ttf"


def probe(final: Path) -> tuple[float, int, int, float]:
    """Trả (duration_giây, width, height, fps) của video bằng ffprobe."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate,duration",
         "-show_entries", "format=duration", "-of", "json", str(final)],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    st = d["streams"][0]
    dur = float(st.get("duration") or d["format"]["duration"])
    num, den = (st.get("r_frame_rate") or "30/1").split("/")
    fps = (float(num) / float(den)) if float(den) else 30.0
    return dur, int(st["width"]), int(st["height"]), fps


def png_size(path: Path) -> tuple[int, int]:
    """Đọc (width, height) từ header IHDR của PNG — khỏi phụ thuộc Pillow."""
    with path.open("rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return (1, 1)
    w, h = struct.unpack(">II", head[16:24])
    return (w, h)


def copy_asset(brand_dir: Path, name: str, dst_name: str, public: Path) -> None:
    src = brand_dir / name
    if not src.exists():
        raise SystemExit(
            f"Thiếu brand asset: {src}\n"
            f"→ preset thiếu file. Chuẩn bị asset trong suốt (RGBA) cho brand rồi đặt vào thư mục preset."
        )
    shutil.copyfile(src, public / dst_name)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="thư mục dự án (chứa project.json + 06_final/final.mp4)")
    ap.add_argument("--brand-config", required=True, help="đường dẫn brand.json (preset)")
    ap.add_argument("--final", help="đường dẫn final.mp4 (mặc định <project>/06_final/final.mp4)")
    ap.add_argument("--tagline", help="tagline end-card biến thiên (mặc định project.json endcard_tagline → preset defaultTagline)")
    ap.add_argument("--intro-sec", type=float, default=2.0, help="thời lượng intro logo ĐỨNG RIÊNG ở đầu (giây); 0 = tắt intro")
    ap.add_argument("--endcard-sec", type=float, default=3.0, help="thời lượng end-card CỘNG THÊM (giây)")
    ap.add_argument("--sonic", help="file nốt chuông mềm — copy vào public/")
    ap.add_argument("--cta-voice", dest="cta_voice", help="file lời đọc CTA cuối — copy vào public/")
    a = ap.parse_args()

    pdir = Path(a.project)
    m = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
    brand = json.loads(Path(a.brand_config).read_text(encoding="utf-8"))
    brand_dir = Path(a.brand_config).resolve().parent
    assets = brand.get("assets", {})
    colors = brand.get("colors", {})

    final = Path(a.final) if a.final else pdir / "06_final" / "final.mp4"
    if not final.exists():
        raise SystemExit(f"Không thấy final.mp4: {final} — ráp ffmpeg (vidgen-assemble) trước đã.")

    dur, w, h, fps = probe(final)
    content_frames = round(dur * fps)
    intro_frames = round(max(0.0, a.intro_sec) * fps)
    endcard_frames = round(a.endcard_sec * fps)
    total_frames = intro_frames + content_frames + endcard_frames

    tagline = a.tagline or m.get("endcard_tagline") or brand.get("defaultTagline", "")

    public = HERE / "public"
    public.mkdir(exist_ok=True)
    shutil.copyfile(final, public / "bg.mp4")

    if FONT_SRC.exists():
        shutil.copyfile(FONT_SRC, public / "BeVietnamPro-Bold.ttf")
    else:
        print(f"⚠ không thấy font {FONT_SRC} — dấu tiếng Việt có thể sai; đặt font vào public/ tay.")

    # Copy asset preset trong suốt vào public/ (tên chuẩn hoá).
    copy_asset(brand_dir, assets.get("logoLockup", "logo_lockup.png"), "logo_lockup.png", public)
    copy_asset(brand_dir, assets.get("logoMark", "logo_mark.png"), "logo_mark.png", public)
    copy_asset(brand_dir, assets.get("hero", "hero.png"), "hero.png", public)
    hw, hh = png_size(public / "hero.png")
    hero_aspect = f"{hw} / {hh}"

    sonic_file = ""
    if a.sonic:
        sp = Path(a.sonic)
        if not sp.exists():
            raise SystemExit(f"Không thấy file nốt chuông: {sp}")
        sonic_file = "sonic" + sp.suffix
        shutil.copyfile(sp, public / sonic_file)

    cta_voice_file = ""
    if a.cta_voice:
        cp = Path(a.cta_voice)
        if not cp.exists():
            raise SystemExit(f"Không thấy file lời CTA: {cp}")
        cta_voice_file = "cta_voice" + cp.suffix
        shutil.copyfile(cp, public / cta_voice_file)

    props = {
        "bg": "bg.mp4",
        "durationInFrames": total_frames,
        "introDurationInFrames": intro_frames,
        "contentDurationInFrames": content_frames,
        "endCardDurationInFrames": endcard_frames,
        "fps": round(fps),
        "width": w,
        "height": h,
        "endcardTagline": tagline,
        "brandName": brand.get("wordmark", ""),
        "ctaUrl": brand.get("ctaUrl", ""),
        "colorBgTop": colors.get("bgTop", "#FDF6EC"),
        "colorBgBottom": colors.get("bgBottom", "#FBE4D2"),
        "colorText": colors.get("text", "#3E5A87"),
        "logoLockup": "logo_lockup.png",
        "logoMark": "logo_mark.png",
        "heroImg": "hero.png",
        "heroAspect": hero_aspect,
        "fontFile": "BeVietnamPro-Bold.ttf",
        "sonicFile": sonic_file,
        "ctaVoiceFile": cta_voice_file,
    }
    (HERE / "props.json").write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ props.json: {w}x{h} @ {round(fps)}fps")
    print(f"  intro {intro_frames}f ({max(0.0, a.intro_sec):.1f}s) + nội dung {content_frames}f ({dur:.1f}s) + end-card {endcard_frames}f ({a.endcard_sec:.1f}s) = {total_frames}f")
    print(f"  brand={brand.get('wordmark')!r} tagline={tagline!r}")
    print(f"  sonic: {sonic_file or '—'} | cta-voice: {cta_voice_file or '—'}")
    out = final.with_name("final_overlay.mp4")
    print("\nRender:")
    print(f"  npx remotion render VidgenOverlay {out} --props=props.json")


if __name__ == "__main__":
    main()

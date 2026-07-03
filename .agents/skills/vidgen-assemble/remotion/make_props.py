#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_props.py — sinh props.json cho Remotion overlay (opt-in) từ project.json + final.mp4.

Chuẩn bị mọi thứ để `npx remotion render VidgenOverlay out.mp4 --props=props.json`:
  1. Đo duration + kích thước bản final (ffprobe).
  2. Copy final.mp4 → public/bg.mp4, copy font Be Vietnam Pro → public/ (giữ dấu tiếng Việt).
  3. Ghi props.json (hookText lấy từ project.json hook, endCardText từ --endcard-text).

Chạy trong thư mục remotion/ này:
  python make_props.py --project ../../../projects/<tên> --endcard-text "Theo dõi để xem tiếp"
  npx remotion render VidgenOverlay ../../../projects/<tên>/06_final/final_overlay.mp4 --props=props.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True, help="thư mục dự án (chứa project.json + 06_final/final.mp4)")
    ap.add_argument("--final", help="đường dẫn final.mp4 (mặc định <project>/06_final/final.mp4)")
    ap.add_argument("--hook", help="câu hook/title (mặc định lấy từ project.json hook.spoken/promise)")
    ap.add_argument("--endcard-text", dest="endcard_text", default="", help="chữ end-card (brand/CTA)")
    ap.add_argument("--title-sec", type=float, default=3.0, help="thời lượng hiện title (giây)")
    ap.add_argument("--endcard-sec", type=float, default=3.0, help="thời lượng end-card (giây)")
    a = ap.parse_args()

    pdir = Path(a.project)
    m = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
    final = Path(a.final) if a.final else pdir / "06_final" / "final.mp4"
    if not final.exists():
        raise SystemExit(f"Không thấy final.mp4: {final} — ráp ffmpeg (vidgen-assemble) trước đã.")

    dur, w, h, fps = probe(final)
    total_frames = round(dur * fps)
    hook = m.get("hook", {}) or {}
    hook_text = a.hook if a.hook is not None else (hook.get("spoken") or hook.get("promise") or "")

    public = HERE / "public"
    public.mkdir(exist_ok=True)
    shutil.copyfile(final, public / "bg.mp4")
    if FONT_SRC.exists():
        shutil.copyfile(FONT_SRC, public / "BeVietnamPro-Bold.ttf")
    else:
        print(f"⚠ không thấy font {FONT_SRC} — dấu tiếng Việt có thể sai; đặt font vào public/ tay.")

    props = {
        "bg": "bg.mp4",
        "durationInFrames": total_frames,
        "fps": round(fps),
        "width": w,
        "height": h,
        "hookText": hook_text,
        "endCardText": a.endcard_text,
        "titleDurationInFrames": round(a.title_sec * fps),
        "endCardDurationInFrames": round(a.endcard_sec * fps),
        "fontFile": "BeVietnamPro-Bold.ttf",
    }
    (HERE / "props.json").write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ props.json: {w}x{h} @ {round(fps)}fps, {total_frames} frames ({dur:.1f}s)")
    print(f"  hookText: {hook_text!r}")
    print(f"  endCardText: {a.endcard_text!r}")
    out = final.with_name("final_overlay.mp4")
    print("\nRender:")
    print(f"  npx remotion render VidgenOverlay {out} --props=props.json")


if __name__ == "__main__":
    main()

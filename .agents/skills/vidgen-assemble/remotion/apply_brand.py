#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""apply_brand.py — MỘT LỆNH áp bộ nhận diện thương hiệu lên bản ráp cuối.

Engine GENERIC: brand đến từ PRESET `assets/brands/<tên>/brand.json` (--brand bắt buộc chỉ định).
Từ `<project>/06_final/final.mp4` → `final_overlay.mp4`: intro logo → watermark + end-card
(hero nở + tagline + wordmark + url) + nốt chuông + lời CTA.

Tự lo mọi tiền đề (fail-fast, idempotent):
  1. node_modules — thiếu thì `npm install`.
  2. Lời CTA khớp TAGLINE — sinh bằng ElevenLabs **eleven_v3** (model CÓ tiếng Việt; KHÔNG dùng
     multilingual_v2 vì thiếu `vi` → đọc lơ lớ). Tagline mặc định → tái dùng CTA dựng sẵn của preset.
  3. Tự lấy ELEVENLABS_API_KEY qua zsh nếu môi trường thiếu (key set không-export ở ~/.zshenv).
  4. make_props (đo nội dung + cộng end-card khớp độ dài lời CTA) → `npx remotion render`.

Chạy trong thư mục remotion/ này:
  ~/.venv/claude/bin/python apply_brand.py --project ../../../projects/<tên> --brand <tên-brand>
Tùy chọn:
  --brand <tên>                            # preset ở assets/brands/<tên>/ (BẮT BUỘC)
  --tagline "Câu tagline end-card"         # override; mặc định project.json endcard_tagline → preset
  --voice <id>                             # override giọng CTA (mặc định lấy từ brand.json)
  --no-cta / --no-sonic
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
BRANDS_DIR = REPO_ROOT / "assets" / "brands"
TTS_MODEL = "eleven_v3"  # BẮT BUỘC model có tiếng Việt


def sh(cmd: list[str], **kw) -> None:
    print("  $", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def ensure_node() -> None:
    if not (HERE / "node_modules").exists():
        print("• Thiếu node_modules → npm install (lần đầu, nặng)")
        sh(["npm", "install"], cwd=HERE)


def eleven_key() -> str:
    """Lấy ELEVENLABS_API_KEY. Nếu môi trường thiếu (key set KHÔNG export trong ~/.zshenv),
    tự đọc qua zsh login-interactive — để 'một lệnh' chạy thẳng, khỏi bọc zsh -lic."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if key:
        return key
    try:
        key = subprocess.run(
            ["zsh", "-lic", "print -rn -- $ELEVENLABS_API_KEY"],
            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        key = ""
    if not key:
        raise SystemExit(
            "Không lấy được ELEVENLABS_API_KEY. Sửa gốc: thêm `export` ở ~/.zshenv "
            "(dòng `ELEVENLABS_API_KEY=...` → `export ELEVENLABS_API_KEY=...`)."
        )
    return key


def gen_cta(text: str, voice: str, out: Path) -> None:
    key = eleven_key()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128"
    body = json.dumps({
        "text": text,
        "model_id": TTS_MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key, "Content-Type": "application/json",
    })
    print(f"• Sinh lời CTA ({TTS_MODEL}, giọng {voice}): {text!r}")
    with urllib.request.urlopen(req) as r:  # noqa: S310
        data = r.read()
    if data[:3] != b"ID3" and data[:2] != b"\xff\xfb":
        raise SystemExit(f"TTS trả về không phải mp3: {data[:200]!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


def probe_dur(f: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", str(f)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--brand", required=True, help="preset ở assets/brands/<tên>/")
    ap.add_argument("--tagline")
    ap.add_argument("--voice")
    ap.add_argument("--no-cta", action="store_true")
    ap.add_argument("--no-sonic", action="store_true")
    a = ap.parse_args()

    pdir = Path(a.project).resolve()
    manifest = json.loads((pdir / "project.json").read_text(encoding="utf-8"))

    brand_dir = BRANDS_DIR / a.brand
    brand_cfg = brand_dir / "brand.json"
    if not brand_cfg.exists():
        raise SystemExit(f"Không thấy preset brand: {brand_cfg}\n→ tạo assets/brands/{a.brand}/brand.json + asset.")
    brand = json.loads(brand_cfg.read_text(encoding="utf-8"))
    assets = brand.get("assets", {})
    default_tagline = brand.get("defaultTagline", "")

    tagline = a.tagline or manifest.get("endcard_tagline") or default_tagline
    voice = a.voice or brand.get("voice", "")

    ensure_node()

    # Lời CTA: tagline mặc định → tái dùng bản dựng sẵn của preset; khác → sinh mới khớp tagline.
    cta_path = None
    if not a.no_cta:
        cta_default = brand_dir / assets.get("ctaDefault", "cta_default.mp3")
        if tagline == default_tagline and cta_default.exists():
            cta_path = cta_default
            print(f"• Dùng CTA mặc định của preset: {cta_path}")
        else:
            if not voice:
                raise SystemExit(f"Preset {a.brand} thiếu 'voice' để sinh CTA; thêm vào brand.json hoặc --voice.")
            spoken = brand.get("spokenUrl", brand.get("ctaUrl", ""))
            wordmark = brand.get("wordmark", "")
            cta_path = pdir / "04_audio" / "brand_cta.mp3"
            gen_cta(f"{tagline}. {wordmark}, tại {spoken}.", voice, cta_path)

    endcard_sec = 3.0
    if cta_path:
        endcard_sec = round(probe_dur(cta_path) + 1.2, 1)

    sonic = brand_dir / assets.get("sonic", "sonic_chime.mp3")
    args = [sys.executable, str(HERE / "make_props.py"), "--project", str(pdir),
            "--brand-config", str(brand_cfg), "--tagline", tagline, "--endcard-sec", str(endcard_sec)]
    if sonic.exists() and not a.no_sonic:
        args += ["--sonic", str(sonic)]
    if cta_path:
        args += ["--cta-voice", str(cta_path)]
    sh(args, cwd=HERE)

    out = pdir / "06_final" / "final_overlay.mp4"
    sh(["npx", "remotion", "render", "VidgenOverlay", str(out),
        "--props=props.json", "--concurrency=4"], cwd=HERE)
    print(f"\n✓ Bản có brand ({a.brand}): {out}")


if __name__ == "__main__":
    main()

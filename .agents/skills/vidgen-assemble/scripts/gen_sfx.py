#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_sfx.py — Producer cho scenes[].sfx[]: gen file hiệu ứng âm thanh (ElevenLabs Sound Effects)
cho các cảnh, lưu vào 05_audio/sfx/sfxNN.mp3. assemble.py (apply_sfx_layer) sẽ tiêu thụ + mix.

Vì sao tồn tại: clip Veo tự sinh audio nhưng assemble bỏ (-an) do Veo hay lồng giọng-bịa tiếng Anh
đè lời đọc. Field sfx[] vì thế từng MỒ CÔI (khai mà không ai dùng). Script này là đường tiêu thụ:
sfx[] → file SFX sạch, kiểm soát → lớp thứ 3 dưới giọng.

Chế độ 2 — AMBIENCE (keo dán #1 tầng dựng): --ambience gen 1 file room tone ~22s từ
`music.ambience` (manifest) → 05_audio/ambience.mp3; assemble tự loop-crossfade phủ TRỌN video,
volume thấp không ducking — lớp nền LIỀN MẠCH xuyên mọi cắt "dán" các clip gen rời thành một
không gian (thiếu nó, cắt rơi vào im lặng phi tự nhiên).

Cần ELEVENLABS_API_KEY (export). Ví dụ:
  ~/.venv/claude/bin/python gen_sfx.py --project projects/<tên>              # gen mọi cảnh có sfx[]
  ~/.venv/claude/bin/python gen_sfx.py --project projects/<tên> --scenes 2,5,14   # chọn cảnh chủ chốt
  ~/.venv/claude/bin/python gen_sfx.py --project projects/<tên> --ambience       # room tone liền mạch
"""
import argparse
import json
import os
from pathlib import Path


def scene_dur(sid, timings, fallback):
    for t in timings:
        if int(t["id"]) == sid:
            return max(1.0, min(22.0, float(t["end"]) - float(t["start"])))
    return fallback


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--scenes", default="", help="danh sách id cảnh cần gen (vd '2,5,14'); rỗng = mọi cảnh có sfx[]")
    ap.add_argument("--prompt-influence", type=float, default=0.4)
    ap.add_argument("--force", action="store_true", help="gen đè cả khi file đã tồn tại")
    ap.add_argument("--ambience", action="store_true",
                    help="gen ROOM TONE liền mạch (~22s, loopable) từ music.ambience trong manifest "
                         "→ 05_audio/ambience.mp3; assemble tự loop-crossfade phủ trọn video")
    a = ap.parse_args()

    if not os.environ.get("ELEVENLABS_API_KEY"):
        raise SystemExit("Thiếu ELEVENLABS_API_KEY trong môi trường. Biến có thể chưa EXPORT — "
                         "chạy: export ELEVENLABS_API_KEY  (mỗi shell mới phải export lại).")

    pdir = Path(a.project)
    m = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
    tp = pdir / "05_audio" / "timings.json"
    timings = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else []
    sfx_dir = pdir / "05_audio" / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)

    want = {int(x) for x in a.scenes.split(",") if x.strip()} if a.scenes else None

    from elevenlabs import ElevenLabs
    client = ElevenLabs()

    if a.ambience:
        # Chế độ ambience: 1 file room tone loopable — mô tả lấy từ music.ambience (project-level).
        music = m.get("music") if isinstance(m.get("music"), dict) else {}
        text = ((music or {}).get("ambience") or "").strip()
        if not text:
            raise SystemExit('Manifest chưa có music.ambience — điền mô tả room tone (EN), vd: '
                             '"quiet rural village night, soft wind, distant crickets, continuous '
                             'ambient bed, no melody, no sudden events, seamless loop".')
        out = pdir / "05_audio" / "ambience.mp3"
        if out.exists() and not a.force:
            raise SystemExit(f"{out} đã có — dùng --force để gen đè.")
        audio = client.text_to_sound_effects.convert(
            text=text, duration_seconds=22.0, prompt_influence=a.prompt_influence)
        with open(out, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        print(f'🌫 ambience [22.0s] ← "{text}" → {out}\n'
              "assemble.py tự loop-crossfade phủ trọn video (--ambience auto, --ambience-vol 0.25).")
        return

    done, skipped = [], []
    for s in m.get("scenes", []):
        sid = int(s["id"])
        sfx = s.get("sfx") or []
        if not sfx:
            continue
        if want is not None and sid not in want:
            continue
        out = sfx_dir / f"sfx{sid:02d}.mp3"
        if out.exists() and not a.force:
            skipped.append(sid)
            continue
        prompt = ", ".join(sfx)
        d = scene_dur(sid, timings, float(s.get("duration", 6)))
        audio = client.text_to_sound_effects.convert(
            text=prompt, duration_seconds=d, prompt_influence=a.prompt_influence)
        with open(out, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        done.append(sid)
        print(f"  cảnh {sid:2d} [{d:.1f}s] ← \"{prompt}\" → {out.name}")

    print(f"Xong. Gen {len(done)} SFX {done}"
          + (f" · bỏ qua (đã có) {skipped}" if skipped else "")
          + ". assemble.py tự mix (—sfx auto).")


if __name__ == "__main__":
    main()

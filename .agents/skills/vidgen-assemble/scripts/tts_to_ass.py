#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tts_to_ass.py — TTS ElevenLabs (timestamp từng chữ) → narration.mp3 + subs.ass + timings.json.

Phụ đề mặc định là KARAOKE word-level (tô sáng chạy theo từng chữ bằng tag ASS \\kf) — tận dụng
timestamp từng ký tự ElevenLabs vốn đã trả sẵn. Quy ước styling từ nguồn craft (xem
vidgen-assemble/references/caption-and-audio.md): highlight vàng/cyan trên nền trắng, viền đen,
4-6 chữ/dòng, nằm trong safe-zone 9:16. Dùng --plain để quay lại phụ đề tĩnh (không karaoke).

LƯU Ý (chánh kiến): karaoke là quy ước DỄ ĐỌC trên mạng xã hội (xem không tiếng), KHÔNG phải "đòn
bẩy retention có số liệu" — mọi con số kiểu phụ đề +X% retention đã bị research bác, đừng hứa.

Đầu vào là --project (đọc lời đọc từng cảnh trong project.json) HOẶC --text/--text-file.
Với --project: xuất thêm 05_audio/timings.json = [{"id":1,"start":0.0,"end":7.42}, ...]
(thời điểm thật từng cảnh trong file giọng — assemble.py dùng để khớp clip với lời).

Cần: pip install elevenlabs · env ELEVENLABS_API_KEY.
Ví dụ:
  ~/.venv/claude/bin/python tts_to_ass.py --project projects/con-cao --voice VOICE_ID
  ~/.venv/claude/bin/python tts_to_ass.py --project projects/con-cao --voice VOICE_ID --highlight cyan
  ~/.venv/claude/bin/python tts_to_ass.py --text-file loi.txt --voice VOICE_ID --aspect landscape --plain
"""
import argparse
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

RES = {"portrait": (1080, 1920), "landscape": (1920, 1080)}

# ASS color = &HAABBGGRR (BGR order). highlight = đang đọc; base = chưa đọc.
COLORS = {"yellow": "&H0000FFFF", "cyan": "&H00FFFF00", "white": "&H00FFFFFF",
          "green": "&H0000FF00", "pink": "&H00B469FF"}
WHITE = "&H00FFFFFF"
BLACK = "&H00000000"

# Style dùng CHUẨN V4+ (có SecondaryColour — bắt buộc cho karaoke \\kf).
# Karaoke: PrimaryColour = màu highlight (chữ đã/đang quét), SecondaryColour = màu chờ (chưa quét).
HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
ScaledBorderAndShadow: yes
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},{size},{primary},{secondary},{outline_c},&H64000000,1,0,0,0,100,100,0.6,0,1,{outline},2,2,70,70,{marginv},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def fmt(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_words(chars, st, en):
    """Ghép timestamp ký tự → danh sách từ [(text, start, end)]. Space là ranh giới."""
    words, cur, ws, we = [], "", None, None
    for ch, s, e in zip(chars, st, en):
        if ch in (" ", "\n", "\t"):
            if cur:
                words.append((cur, ws, we)); cur, ws = "", None
            continue
        if not cur:
            ws = s
        cur += ch; we = e
    if cur:
        words.append((cur, ws, we))
    return words


def group_lines(words, max_words):
    """Gom từ thành dòng: ngắt ở dấu kết câu hoặc khi đủ max_words."""
    lines, cur = [], []
    for w in words:
        cur.append(w)
        tail = w[0].rstrip()
        ends = tail[-1:] in ".!?…:" if tail else False
        if len(cur) >= max_words or ends:
            lines.append(cur); cur = []
    if cur:
        lines.append(cur)
    return lines


def karaoke_text(line):
    """Dựng text 1 dòng với tag \\kf (fill sweep) khớp thời lượng từng chữ."""
    parts = []
    for i, (t, s, e) in enumerate(line):
        nxt = line[i + 1][1] if i + 1 < len(line) else e
        dur_cs = max(1, round((nxt - s) * 100))  # centiseconds; gồm cả khoảng lặng sau chữ
        parts.append(f"{{\\kf{dur_cs}}}{t} ")
    return "".join(parts).rstrip()


# ─────────────────────────────────────────────────────────────────────────────
# ĐƯỜNG ĐA GIỌNG (per-scene) — kích hoạt khi manifest có scenes[].dialogue[].
# Narrator thuần (không dialogue) VẪN đi đường 1-lệnh cũ ở main() — backward-compat.
# Mô hình P1: mỗi cảnh HOẶC vo (narrator) HOẶC dialogue[] (nhân vật). Consumer cho dialogue[].
# ─────────────────────────────────────────────────────────────────────────────

def has_multivoice(m):
    """True nếu bất kỳ cảnh nào có dialogue[] không rỗng → chuyển sang đường per-scene."""
    for s in m.get("scenes", []):
        if any((d.get("line") or "").strip() for d in (s.get("dialogue") or [])):
            return True
    return False


def voice_map(m):
    """Map char_id → voice_id (chỉ nhân vật đã gán voice_id)."""
    d = {}
    for c in m.get("characters", []):
        vid = (c.get("voice_id") or "").strip()
        if vid:
            d[c["id"]] = vid
    return d


def scene_segments(scene, vmap, narrator, missing):
    """Trả danh sách (voice_id, text) cho 1 cảnh theo mô hình P1.
    - Có dialogue[] → mỗi lượt là 1 segment với giọng nhân vật (thiếu voice_id → fallback narrator).
    - Không dialogue nhưng có vo → 1 segment giọng narrator.
    - Không gì → rỗng (cảnh câm, không vào timings)."""
    dlg = [d for d in (scene.get("dialogue") or []) if (d.get("line") or "").strip()]
    if dlg:
        segs = []
        for d in dlg:
            cid = d.get("char")
            v = vmap.get(cid)
            if not v:
                missing.add(cid)
                v = narrator
            segs.append((v, d["line"].strip()))
        return segs
    vo = (scene.get("vo") or "").strip()
    return [(narrator, vo)] if vo else []


def probe_dur(p):
    """Thời lượng thật của file audio (ffprobe) — dùng làm mốc nối chính xác."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nk=1:nw=1", str(p)],
        capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def tts_segment(ec, voice, text, model, vs):
    """1 lệnh TTS có timestamp → (audio_bytes, chars, starts, ends)."""
    r = ec.text_to_speech.convert_with_timestamps(
        voice_id=voice, text=text, model_id=model, voice_settings=vs)
    b64 = getattr(r, "audio_base_64", None) or getattr(r, "audio_base64", None)
    if not b64:
        raise SystemExit("ElevenLabs không trả audio_base64 — kiểm response/model.")
    al = r.alignment
    return (base64.b64decode(b64), al.characters,
            al.character_start_times_seconds, al.character_end_times_seconds)


def generate_per_scene(a, m, pdir, aspect, ec, vs):
    """Ráp audio đa giọng: TTS từng cảnh đúng giọng → nối (chèn khoảng lặng giữa các lượt/cảnh)
    → narration.mp3 + subs.ass + timings.json. Mốc thời gian đo từ độ dài audio THẬT (ffprobe)
    nên khớp chính xác với file nối — hợp đồng với assemble.py không đổi."""
    narrator = a.voice
    vmap = voice_map(m)
    missing = set()

    w, h = RES.get(aspect, RES["portrait"])
    size = a.size or (62 if aspect == "portrait" else 52)
    marginv = a.marginv or (700 if aspect == "portrait" else 90)
    primary = WHITE if a.plain else COLORS[a.highlight]
    secondary = WHITE

    audio_dir = pdir / "05_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    out_audio = a.out_audio or str(audio_dir / "narration.mp3")
    out_ass = a.out_ass or str(audio_dir / "subs.ass")
    out_timings = audio_dir / "timings.json"

    work = Path(tempfile.mkdtemp(prefix="vidgen_tts_"))
    sil = work / "sil.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=mono", "-t", f"{a.gap:.3f}", str(sil)],
                   check=True)

    concat_list = []   # đường dẫn wav theo thứ tự nối (segment + silence xen kẽ)
    all_lines = []     # dòng sub đã gom (offset toàn cục), KHÔNG gộp xuyên segment/người nói
    timings = []
    offset = 0.0
    seg_i = 0
    for s in m["scenes"]:
        segs = scene_segments(s, vmap, narrator, missing)
        if not segs:
            continue
        scene_start = offset
        for voice, txt in segs:
            audio, chars, st, en = tts_segment(ec, voice, txt, a.model, vs)
            raw = work / f"seg{seg_i:03d}.mp3"
            wav = work / f"seg{seg_i:03d}.wav"
            raw.write_bytes(audio)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw),
                            "-ar", "44100", "-ac", "1", str(wav)], check=True)
            d = probe_dur(wav)
            # gom từ của segment này, cộng offset toàn cục, gom dòng RIÊNG (không lẫn người nói)
            words = [(t, ws + offset, we + offset)
                     for (t, ws, we) in build_words(chars, st, en)
                     if ws is not None and we is not None]
            all_lines.extend(group_lines(words, max(2, a.max_words)))
            concat_list.append(wav)
            offset += d
            concat_list.append(sil)
            offset += a.gap
            seg_i += 1
        scene_end = offset - a.gap  # trừ khoảng lặng đuôi vừa cộng
        timings.append({"id": s["id"], "start": round(scene_start, 3), "end": round(scene_end, 3)})

    if not concat_list:
        raise SystemExit("Không có vo lẫn dialogue nào trong manifest — không gen được audio.")
    if concat_list and concat_list[-1] == sil:
        concat_list.pop()  # bỏ khoảng lặng đuôi cuối cùng

    # nối bằng concat demuxer (mọi wav cùng 44100/mono → an toàn) → mp3
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in concat_list), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "2", str(out_audio)],
                   check=True)

    # subs.ass từ các dòng đã gom
    with open(out_ass, "w", encoding="utf-8") as f:
        f.write(HEAD.format(w=w, h=h, font=a.font, size=size, outline=a.outline,
                            marginv=marginv, primary=primary, secondary=secondary,
                            outline_c=BLACK))
        for line in all_lines:
            if not line:
                continue
            lstart, lend = line[0][1], line[-1][2]
            if lstart is None or lend is None:
                continue
            body = " ".join(t for t, _, _ in line) if a.plain else karaoke_text(line)
            f.write(f"Dialogue: 0,{fmt(lstart)},{fmt(lend)},Sub,,0,0,0,,{body}\n")

    out_timings.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")

    if missing:
        print(f"⚠ Nhân vật thiếu voice_id (dùng giọng narrator thay): {sorted(missing)}")
    kind = "tĩnh" if a.plain else f"karaoke ({a.highlight})"
    print(f"🎙 đa giọng (per-scene): {out_audio} ({offset:.1f}s) · sub {kind}: {out_ass} "
          f"({len(all_lines)} dòng) · timings: {out_timings}")


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--project", help="thư mục dự án (đọc vo từng cảnh trong project.json)")
    src.add_argument("--text")
    src.add_argument("--text-file", dest="text_file")
    ap.add_argument("--voice", required=True, help="ElevenLabs voice id")
    ap.add_argument("--model", default="eleven_v3")
    ap.add_argument("--aspect", default="", help="portrait/landscape (mặc định: lấy từ project.json)")
    ap.add_argument("--font", default="Be Vietnam Pro")
    ap.add_argument("--size", type=int, default=0, help="cỡ chữ (mặc định 62 dọc / 52 ngang)")
    ap.add_argument("--marginv", type=int, default=0, help="lề dưới sub (mặc định 700 dọc — safe-zone / 90 ngang)")
    ap.add_argument("--out-audio", dest="out_audio", default="")
    ap.add_argument("--out-ass", dest="out_ass", default="")
    ap.add_argument("--stability", type=float, default=0.5)
    ap.add_argument("--similarity", type=float, default=0.75)
    ap.add_argument("--style", type=float, default=0.3)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--plain", action="store_true", help="phụ đề tĩnh (KHÔNG karaoke)")
    ap.add_argument("--highlight", default="yellow", choices=list(COLORS),
                    help="màu chữ đang đọc (karaoke). Mặc định yellow — tương phản tốt trên nền trắng")
    ap.add_argument("--max-words", dest="max_words", type=int, default=5,
                    help="số chữ tối đa mỗi dòng sub (nguồn khuyên 4-6)")
    ap.add_argument("--outline", type=int, default=4, help="độ dày viền chữ (px)")
    ap.add_argument("--gap", type=float, default=0.25,
                    help="khoảng lặng (giây) chèn giữa các lượt thoại/cảnh ở ĐƯỜNG ĐA GIỌNG "
                         "(kích hoạt khi có dialogue[]). Cho nhịp thở giữa các lượt; 0 = nối sát")
    a = ap.parse_args()

    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit(
            "Thiếu ELEVENLABS_API_KEY trong môi trường của tiến trình Python.\n"
            "  Lưu ý RANH GIỚI môi trường→script: key có thể là SHELL VAR chưa EXPORT (zsh thấy\n"
            "  nhưng tiến trình con không thấy). Chạy qua: zsh -lic 'export ELEVENLABS_API_KEY; "
            "~/.venv/claude/bin/python .../tts_to_ass.py ...'\n"
            "  Kiểm nhanh: zsh -lic 'export ELEVENLABS_API_KEY; python -c \"import os;"
            "print(bool(os.environ.get(\\\"ELEVENLABS_API_KEY\\\")))\"'")

    vs = {"stability": a.stability, "similarity_boost": a.similarity,
          "style": a.style, "speed": a.speed}

    # ── ĐƯỜNG ĐA GIỌNG: manifest có dialogue[] → per-scene (giọng riêng mỗi nhân vật) ──
    if a.project:
        _pdir = Path(a.project)
        _m = json.loads((_pdir / "project.json").read_text(encoding="utf-8"))
        if has_multivoice(_m):
            from elevenlabs import ElevenLabs
            ec = ElevenLabs(api_key=key)
            generate_per_scene(a, _m, _pdir, a.aspect or _m.get("aspect", "portrait"), ec, vs)
            return

    # ── gom text + ranh giới cảnh (ĐƯỜNG 1-LỆNH cũ — narrator thuần) ──
    scene_bounds = []  # (scene_id, start_idx, end_idx) trong chuỗi text ghép
    if a.project:
        pdir = Path(a.project)
        m = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
        aspect = a.aspect or m.get("aspect", "portrait")
        parts, pos = [], 0
        for s in m["scenes"]:
            vo = (s.get("vo") or "").strip()
            if not vo:
                continue
            parts.append(vo)
            scene_bounds.append((s["id"], pos, pos + len(vo)))
            pos += len(vo) + 1  # +1 cho khoảng trắng nối
        text = " ".join(parts)
        audio_dir = pdir / "05_audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        out_audio = a.out_audio or str(audio_dir / "narration.mp3")
        out_ass = a.out_ass or str(audio_dir / "subs.ass")
        out_timings = audio_dir / "timings.json"
    else:
        text = a.text if a.text else open(a.text_file, encoding="utf-8").read().strip()
        aspect = a.aspect or "portrait"
        out_audio = a.out_audio or "narration.mp3"
        out_ass = a.out_ass or "subs.ass"
        out_timings = None

    w, h = RES.get(aspect, RES["portrait"])
    size = a.size or (62 if aspect == "portrait" else 52)
    marginv = a.marginv or (700 if aspect == "portrait" else 90)
    primary = WHITE if a.plain else COLORS[a.highlight]
    secondary = WHITE  # màu chờ (chưa quét) = trắng

    # ── TTS ──
    from elevenlabs import ElevenLabs
    ec = ElevenLabs(api_key=key)
    r = ec.text_to_speech.convert_with_timestamps(
        voice_id=a.voice, text=text, model_id=a.model,
        voice_settings={"stability": a.stability, "similarity_boost": a.similarity,
                        "style": a.style, "speed": a.speed})
    b64 = getattr(r, "audio_base_64", None) or getattr(r, "audio_base64", None)
    if not b64:
        raise SystemExit("ElevenLabs không trả audio_base64 — kiểm response/model.")
    open(out_audio, "wb").write(base64.b64decode(b64))
    al = r.alignment
    chars, st, en = al.characters, al.character_start_times_seconds, al.character_end_times_seconds

    # ── sub .ass: karaoke word-level (mặc định) hoặc tĩnh (--plain) ──
    words = build_words(chars, st, en)
    lines = group_lines(words, max(2, a.max_words))
    with open(out_ass, "w", encoding="utf-8") as f:
        f.write(HEAD.format(w=w, h=h, font=a.font, size=size, outline=a.outline,
                            marginv=marginv, primary=primary, secondary=secondary,
                            outline_c=BLACK))
        for line in lines:
            if not line:
                continue
            lstart, lend = line[0][1], line[-1][2]
            if lstart is None or lend is None:
                continue
            body = " ".join(t for t, _, _ in line) if a.plain else karaoke_text(line)
            f.write(f"Dialogue: 0,{fmt(lstart)},{fmt(lend)},Sub,,0,0,0,,{body}\n")

    # ── timings.json theo cảnh (map ranh giới ký tự → thời gian thật) ──
    if out_timings and scene_bounds:
        timings = []
        for sid, i0, i1 in scene_bounds:
            i0c = min(i0, len(st) - 1)
            i1c = min(i1 - 1, len(en) - 1)
            timings.append({"id": sid, "start": round(st[i0c], 3), "end": round(en[i1c], 3)})
        out_timings.write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"timings: {out_timings}")

    total = en[-1] if en else 0
    kind = "tĩnh" if a.plain else f"karaoke ({a.highlight})"
    print(f"audio: {out_audio} ({total:.1f}s) · sub {kind}: {out_ass} ({len(lines)} dòng)")


if __name__ == "__main__":
    main()

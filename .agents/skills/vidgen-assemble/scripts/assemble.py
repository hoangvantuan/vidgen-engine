#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assemble.py — Ráp video từ dự án vidgen: clip từng cảnh + giọng kể + sub + nhạc nền → final.mp4.

Đọc projects/<tên>/project.json (+ 05_audio/timings.json nếu có narration):
- Mỗi clip cảnh được đổi tốc độ (setpts, KHÔNG loop → không giật) khớp đúng khoảng
  lời đọc của cảnh đó trong file giọng.
- Không có narration → mỗi cảnh giữ đúng scene.duration.
- Burn sub .ass (bỏ bằng --no-burn để giao CapCut) · nhạc nền ducking theo giọng
  (sidechaincompress) · end-card nán cuối chống cụt.
- KEO DÁN chống "mùi AI" tầng dựng (đợt 2): kéo chậm CÓ TRẦN (--max-slow) + hold frame ·
  grain/LUT thống nhất toàn phim (--grain/--lut) · ambience liền mạch xuyên cắt (--ambience).

Cần: ffmpeg. Ví dụ:
  ~/.venv/claude/bin/python assemble.py --project projects/con-cao --bgm nhac.mp3
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

RES = {"portrait": (1080, 1920), "landscape": (1920, 1080)}


def dur(p):
    return float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nokey=1:noprint_wrappers=1", str(p)]).decode().strip())


def has_subtitles_filter():
    """ffmpeg build thiếu libass (vd bản brew rút gọn) thì không burn sub được."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                         capture_output=True, text=True).stdout
    return " subtitles " in out


def run(cmd):
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("ffmpeg lỗi: " + " ".join(map(str, cmd))[:200])


def resolve_bgm(cli_bgm, music, pdir, bgm_dir):
    """Chọn nhạc nền. Ưu tiên: CLI --bgm > music.file (manifest) > auto-pick theo music.mood.
    Auto-pick tìm trong bgm_dir file khớp mood: <mood>/*.mp3|wav hoặc <mood>*.mp3|wav (lấy file đầu)."""
    if cli_bgm:
        return cli_bgm
    f = (music.get("file") or "").strip()
    if f:
        p = Path(f)
        return str(p if p.is_absolute() else pdir / f)
    mood = (music.get("mood") or "").strip().lower()
    if mood and Path(bgm_dir).is_dir():
        d = Path(bgm_dir)
        cands = (sorted(d.glob(f"{mood}/*.mp3")) + sorted(d.glob(f"{mood}*.mp3"))
                 + sorted(d.glob(f"{mood}/*.wav")) + sorted(d.glob(f"{mood}*.wav")))
        if cands:
            return str(cands[0])
    return ""


def norm_transition(tr):
    """Chấp nhận transition dạng dict {"type","dur"} HOẶC chuỗi "type:dur" (vd "fade:0.5").
    Trả dict hoặc None — chống crash khi manifest ghi chuỗi thay vì dict."""
    if not tr:
        return None
    if isinstance(tr, str):
        parts = tr.split(":")
        return {"type": parts[0], "dur": float(parts[1]) if len(parts) > 1 and parts[1] else 0.5}
    if isinstance(tr, dict):
        return tr
    return None


def apply_ambience_layer(video, amb, vol):
    """KEO DÁN #1 (ngành dựng): room tone/ambience LIỀN MẠCH chạy xuyên mọi cắt "dán" các clip
    gen rời thành một không gian — thiếu nó, cắt rơi vào im lặng phi tự nhiên. Nguồn 1 file ~22s
    (gen_sfx.py --ambience) → loop CÓ CROSSFADE (không seam) phủ trọn video, volume THẤP CỐ ĐỊNH,
    KHÔNG ducking (chính sự liên tục là keo; duck theo giọng sẽ phập phồng lộ). Lớp phủ riêng
    như apply_sfx_layer — không đụng graph mix chính."""
    total, sd, xd = dur(video), dur(amb), 2.0
    n = 1
    while sd + (n - 1) * (sd - xd) < total + 1 and n < 60:
        n += 1
    has_a = bool(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip())
    ins, fc = [], []
    for _ in range(n):
        ins += ["-i", str(amb)]
    prev = "[1:a]"
    for i in range(2, n + 1):
        fc.append(f"{prev}[{i}:a]acrossfade=d={xd}[c{i}]")
        prev = f"[c{i}]"
    fc.append(f"{prev}atrim=0:{total:.3f},volume={vol},afade=t=in:st=0:d=1,"
              f"afade=t=out:st={max(0, total - 2):.2f}:d=2[amb]")
    if has_a:
        fc.append("[0:a][amb]amix=inputs=2:normalize=0:duration=first[mx];"
                  "[mx]alimiter=limit=0.95[aout]")
    else:
        fc.append("[amb]anull[aout]")
    tmp = video.with_name(video.stem + "__ambtmp" + video.suffix)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), *ins,
         "-filter_complex", ";".join(fc), "-map", "0:v", "-c:v", "copy",
         "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)])
    tmp.replace(video)
    print(f"🌫 Ambience liền mạch: {Path(amb).name} loop×{n} crossfade {xd}s, vol={vol} (không duck)")
    return True


def apply_sfx_layer(video, pdir, sfx_vol):
    """Consumer cho scenes[].sfx[] — trộn SFX làm LỚP THỨ 3 (dưới giọng + trên nhạc), đặt đúng
    thời điểm mỗi cảnh theo 05_audio/timings.json. File nguồn: 05_audio/sfx/sfxNN.mp3 (gen bằng
    gen_sfx.py). Nhờ đó field sfx[] KHÔNG còn mồ côi. Không có timings/sfx → bỏ qua, trả False."""
    timings_p = pdir / "05_audio" / "timings.json"
    sfx_dir = pdir / "05_audio" / "sfx"
    if not timings_p.exists() or not sfx_dir.is_dir():
        return False
    timings = json.loads(timings_p.read_text(encoding="utf-8"))
    items = [(sfx_dir / f"sfx{int(t['id']):02d}.mp3", float(t["start"]))
             for t in timings if (sfx_dir / f"sfx{int(t['id']):02d}.mp3").exists()]
    if not items:
        return False
    has_a = bool(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip())
    ins, fc, labels = [], [], []
    for i, (f, start) in enumerate(items):
        ins += ["-i", str(f)]
        fo = max(0.2, dur(f) - 0.5)
        ms = int(start * 1000)
        fc.append(f"[{i + 1}:a]volume={sfx_vol},afade=t=in:st=0:d=0.3,"
                  f"afade=t=out:st={fo:.2f}:d=0.5,adelay={ms}|{ms}[x{i}]")
        labels.append(f"[x{i}]")
    base = ("[0:a]" if has_a else "") + "".join(labels)
    n = len(items) + (1 if has_a else 0)
    dur_mode = "first" if has_a else "longest"
    fc.append(f"{base}amix=inputs={n}:normalize=0:duration={dur_mode}[mx];"
              f"[mx]alimiter=limit=0.95[aout]")
    tmp = video.with_name(video.stem + "__sfxtmp" + video.suffix)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(video), *ins,
         "-filter_complex", ";".join(fc), "-map", "0:v", "-c:v", "copy",
         "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)])
    tmp.replace(video)
    print(f"🔊 SFX layer: trộn {len(items)} hiệu ứng (sfx-vol={sfx_vol}) theo timings")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="thư mục dự án chứa project.json")
    ap.add_argument("--bgm", default="", help="file nhạc nền — override cả music.mood/file trong manifest")
    ap.add_argument("--bgm-dir", default="", help="thư viện nhạc theo mood (mặc định: assets/bgm/ ở root engine)")
    ap.add_argument("--bgm-vol", type=float, default=1.2,
                    help="âm lượng nhạc nền trước ducking (default 1.2 — đủ nghe dưới giọng; tăng nếu nhạc còn nhỏ)")
    ap.add_argument("--sfx", choices=["auto", "on", "off"], default="auto",
                    help="lớp SFX từ 05_audio/sfx/ (auto=mix nếu có file; off=bỏ). Consumer cho scenes[].sfx[]")
    ap.add_argument("--sfx-vol", type=float, default=0.35,
                    help="âm lượng SFX (dưới giọng; default 0.35)")
    ap.add_argument("--ambience", default="auto",
                    help="room tone LIỀN MẠCH xuyên cắt (keo dán clip rời): auto=dùng 05_audio/ambience.mp3 "
                         "nếu có (gen bằng gen_sfx.py --ambience) · off=bỏ · <file>=chỉ định")
    ap.add_argument("--ambience-vol", dest="ambience_vol", type=float, default=0.25,
                    help="âm lượng ambience (THẤP, dưới SFX, không ducking; default 0.25)")
    ap.add_argument("--max-slow", dest="max_slow", type=float, default=1.15,
                    help="TRẦN kéo chậm clip khớp VO (default 1.15 ≈ khó nhận ra); phần thiếu còn lại "
                         "hold frame cuối. Kéo chậm vô hạn = cảm giác trôi nổi. Hành vi cũ: --max-slow 99")
    ap.add_argument("--lut", default="", help="file .cube — 1 color grade THỐNG NHẤT toàn phim "
                    "(ủi chênh màu giữa các clip gen rời), áp trước burn sub")
    ap.add_argument("--grain", type=float, default=5,
                    help="film grain đồng nhất phủ toàn thân video — dán texture giữa clip AI "
                         "(default 5, rất nhẹ; 0=tắt)")
    ap.add_argument("--endcard", default="", help="ảnh end-card cuối (tùy chọn)")
    ap.add_argument("--endcard-dur", type=float, default=2.5)
    ap.add_argument("--tail", type=float, default=1.5, help="giây nán thêm sau khi giọng dứt (chống cụt)")
    ap.add_argument("--xfade", default="", help='transition mặc định cho MỌI cắt cảnh "type:dur" '
                    '(vd "fade:0.5"); từng cảnh override bằng scenes[].transition trong manifest')
    ap.add_argument("--no-burn", action="store_true", help="không burn sub (xuất kit cho CapCut)")
    ap.add_argument("--light", action="store_true", help="xuất thêm bản share nhẹ *_light.mp4 (nén cao)")
    ap.add_argument("--light-crf", dest="light_crf", type=int, default=26, help="CRF bản light (cao=nhẹ, mặc định 26)")
    ap.add_argument("--light-scale", dest="light_scale", type=int, default=0, help="hạ chiều rộng bản light (px, 0=giữ nguyên; vd 720)")
    ap.add_argument("--fonts-dir", default="", help="thư mục font cho sub (mặc định: assets/fonts bundle trong skill)")
    ap.add_argument("--out", default="", help="mặc định: 06_final/final.mp4")
    a = ap.parse_args()

    pdir = Path(a.project)
    m = json.loads((pdir / "project.json").read_text(encoding="utf-8"))
    w, h = RES.get(m.get("aspect", "portrait"), RES["portrait"])
    out = Path(a.out) if a.out else pdir / "06_final" / "final.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    # ── nhạc nền: CLI --bgm > music.file > auto-pick theo music.mood trong assets/bgm/ ──
    music = m.get("music") if isinstance(m.get("music"), dict) else {}
    engine_root = Path(__file__).resolve().parents[4]
    bgm_dir = a.bgm_dir or str(engine_root / "assets" / "bgm")
    bgm = resolve_bgm(a.bgm, music or {}, pdir, bgm_dir)
    if bgm and not a.bgm:
        print(f"♪ nhạc nền tự chọn (mood={(music or {}).get('mood') or 'file'}): {bgm}")
    elif (music or {}).get("mood") and not bgm:
        print(f"⚠ music.mood='{music['mood']}' nhưng không thấy nhạc khớp trong {bgm_dir} — video sẽ không nhạc.")

    narration = pdir / "05_audio" / "narration.mp3"
    ass = pdir / "05_audio" / "subs.ass"
    timings_f = pdir / "05_audio" / "timings.json"
    has_voice = narration.exists()

    # ── cảnh render được: clip done, hoặc fallback Ken Burns từ ảnh (Flow từ chối gen) ──
    scenes, kenburns = [], set()
    for s in m["scenes"]:
        if s.get("clip", {}).get("status") == "done":
            scenes.append(s)
        elif s.get("image", {}).get("file") and (pdir / s["image"]["file"]).exists():
            scenes.append(s)
            kenburns.add(s["id"])
    if not scenes:
        raise SystemExit("Chưa có clip/ảnh nào dùng được trong manifest — chạy vidgen-clips trước.")
    if kenburns:
        print(f"⚠ Cảnh dùng fallback Ken Burns từ ảnh tĩnh (clip chưa có): {sorted(kenburns)}")
    missing = [s["id"] for s in m["scenes"] if s not in scenes]
    if missing:
        print(f"⚠ Cảnh thiếu cả clip lẫn ảnh, sẽ bỏ qua: {missing}")

    # ── thời lượng đích từng cảnh ──
    if has_voice and timings_f.exists():
        tm = {t["id"]: t for t in json.loads(timings_f.read_text(encoding="utf-8"))}
        starts = [tm[s["id"]]["start"] for s in scenes if s["id"] in tm]
        ends = [tm[s["id"]]["end"] for s in scenes if s["id"] in tm]
        targets = []
        for i, s in enumerate(scenes):
            if s["id"] not in tm:
                targets.append(float(s.get("duration", 8)))
            elif i + 1 < len(scenes) and scenes[i + 1]["id"] in tm:
                targets.append(tm[scenes[i + 1]["id"]]["start"] - tm[s["id"]]["start"])
            else:
                targets.append(ends[-1] - tm[s["id"]]["start"] + (0 if a.endcard else a.tail))
        total = (starts[0] if starts else 0) + sum(targets)
    else:
        targets = [float(s.get("duration", 8)) for s in scenes]
        total = sum(targets)

    cover = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    work = Path(tempfile.mkdtemp(prefix="vidgen_"))

    # ── transition sau từng cảnh (giữa i và i+1) ──
    # xfade "ăn" overlap → mỗi cảnh render DƯ đúng phần bị ăn để tổng vẫn khớp narration.
    g = (a.xfade.split(":") + ["0.5"])[:2] if a.xfade else None
    cuts = []  # phần tử i = transition giữa cảnh i và i+1: (type, dur) hoặc None (cắt cứng)
    for i in range(len(scenes) - 1):
        tr = norm_transition(scenes[i].get("transition"))
        if tr is None and g:
            tr = {"type": g[0], "dur": float(g[1])}
        if tr and tr.get("type") not in (None, "", "cut"):
            cuts.append((tr["type"], float(tr.get("dur", 0.5))))
        else:
            cuts.append(None)

    # ── pha 1: chuẩn hóa từng cảnh khớp thời lượng đích ──
    # Flow trả clip 720x1280 → luôn cover-scale lên; Veo tự gắn audio → luôn -an.
    # Retime: clip DÀI hơn đích → cắt (giữ tốc độ thật); NGẮN hơn → làm chậm mượt (setpts).
    norm = []
    for idx, (s, tgt) in enumerate(zip(scenes, targets)):
        tgt += cuts[idx][1] if idx < len(cuts) and cuts[idx] else 0  # bù phần xfade ăn
        o = work / f"n{s['id']:02d}.mp4"
        if s["id"] in kenburns:
            img = pdir / s["image"]["file"]
            frames = max(1, int(tgt * 30))
            run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(img),
                 "-vf", f"scale={w*2}:{h*2}:force_original_aspect_ratio=increase,"
                        f"crop={w*2}:{h*2},zoompan=z='1+0.10*on/{frames}':d={frames}:"
                        f"s={w}x{h}:fps=30,format=yuv420p",
                 "-t", f"{tgt:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(o)])
        else:
            src = pdir / s["clip"]["file"]
            sd = dur(src)
            # Clip DÀI hơn đích → cắt lấy ĐOẠN ĐẦU giữ tốc độ thật (chất lượng clip AI đạt đỉnh
            # 4-6s đầu, đuôi generation hay rã). NGẮN hơn → làm chậm CÓ TRẦN (--max-slow, mặc định
            # 1.15 ≈ dưới ngưỡng mắt bắt slow-mo); phần vẫn thiếu → HOLD frame cuối (tpad clone).
            # Kéo chậm không trần là nguồn cảm giác "trôi nổi" — mùi AI ở tầng dựng.
            ratio = min(max(1.0, tgt / sd), max(1.0, a.max_slow))
            lack = tgt - sd * ratio
            vf = cover + (f",setpts=PTS*{ratio:.6f}" if ratio > 1.001 else "")
            if lack > 0.05:
                vf += f",tpad=stop_mode=clone:stop_duration={lack + 0.2:.3f}"
                (print if lack <= 2.0 else lambda t: print("⚠ " + t))(
                    f"  cảnh {s['id']}: VO dài hơn clip {tgt - sd:.1f}s → chậm x{ratio:.2f} "
                    f"+ hold frame cuối {lack:.1f}s"
                    + ("" if lack <= 2.0 else " — HOLD DÀI, cân lại VO/duration cảnh này (gốc ở storyboard)"))
            vf += ",fps=30,format=yuv420p"
            run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf,
                 "-t", f"{tgt:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(o)])
        norm.append(o)
    if a.endcard:
        o = work / "endcard.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", a.endcard,
             "-vf", f"{cover},fps=30,format=yuv420p",
             "-t", f"{a.endcard_dur + a.tail:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(o)])
        norm.append(o)
        total += a.endcard_dur + a.tail

    # ── pha 2: nối — chuỗi cảnh có transition thì xfade, cắt cứng thì concat ──
    def xfade_join(paths, trans, out_path):
        cmd = ["ffmpeg", "-y", "-v", "error"]
        for p in paths:
            cmd += ["-i", str(p)]
        fg, prev, cum = [], "[0:v]", dur(paths[0])
        for i, (t, d) in enumerate(trans, start=1):
            off = max(0.0, cum - d)
            fg.append(f"{prev}[{i}:v]xfade=transition={t}:duration={d:.3f}:offset={off:.3f}[x{i}]")
            prev = f"[x{i}]"
            cum = off + dur(paths[i])
        cmd += ["-filter_complex", ";".join(fg), "-map", prev,
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(out_path)]
        run(cmd)

    pieces, cur_p, cur_t = [], [norm[0]], []
    for i in range(1, len(norm)):
        tr = cuts[i - 1] if i - 1 < len(cuts) else None
        if tr:
            cur_p.append(norm[i]); cur_t.append(tr)
        else:
            pieces.append((cur_p, cur_t)); cur_p, cur_t = [norm[i]], []
    pieces.append((cur_p, cur_t))

    joined = []
    for j, (ps, ts) in enumerate(pieces):
        if len(ps) == 1:
            joined.append(ps[0])
        else:
            o = work / f"run{j:02d}.mp4"
            xfade_join(ps, ts, o)
            joined.append(o)

    if len(joined) == 1:
        body = joined[0]
    else:
        lst = work / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in joined), encoding="utf-8")
        body = work / "body.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", str(body)])

    skill_dir = Path(__file__).resolve().parents[1]
    _fdir = skill_dir / "assets" / "fonts"                       # font bundle trong skill (Be Vietnam Pro)
    fonts = a.fonts_dir or (str(_fdir) if _fdir.exists() else "")
    can_burn = ass.exists() and not a.no_burn and has_subtitles_filter()
    if ass.exists() and not a.no_burn and not can_burn:
        print("⚠ ffmpeg này thiếu libass (bản brew rút gọn) — không burn được sub. "
              "Sẽ xuất sub rời cạnh final. Cài bản đủ: brew reinstall ffmpeg (cần --enable-libass).")

    def esc(p):  # path trong filter graph phải escape : \ '
        return str(p).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    # KEO DÁN #2: grade + grain THỐNG NHẤT toàn thân video (ủi chênh màu/texture giữa các clip
    # gen rời — mỗi generation một "chất" ảnh hơi khác). Áp TRƯỚC burn sub để chữ sạch.
    vf = []
    if a.lut:
        vf.append(f"lut3d=file='{esc(a.lut)}'")
    if a.grain > 0:
        vf.append(f"noise=alls={a.grain:g}:allf=t+u")
    if can_burn:
        vf.append(f"subtitles=filename='{esc(ass)}'" + (f":fontsdir='{esc(fonts)}'" if fonts else ""))

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(body)]
    fc, amap = [], None
    if has_voice:
        cmd += ["-i", str(narration)]
        if bgm:
            cmd += ["-stream_loop", "-1", "-i", bgm]
            # ducking dịu (ratio 3:1, threshold 0.06) — nhạc LÙI dưới giọng nhưng vẫn NGHE RÕ.
            # Default cũ ratio=4/threshold=0.03 nén nhạc gần như tắt vì giọng đọc gần liên tục.
            # Pad giọng tới hết video TRƯỚC sidechain — nếu không, sidechaincompress dừng khi
            # narration hết (giọng ngắn hơn nhạc) → nhạc bị cắt sớm. Sau khi giọng hết, [voc] im
            # nên nhạc hết bị ducking → vang đầy tự nhiên tới cuối.
            fc.append(f"[1:a]apad=whole_dur={total:.3f},asplit=2[voc1][voc2];"
                      f"[2:a]volume={a.bgm_vol}[b];[b][voc1]sidechaincompress="
                      f"threshold=0.06:ratio=3:attack=15:release=300[duck];"
                      f"[voc2][duck]amix=inputs=2:duration=first:dropout_transition=0[aout]")
            amap = "[aout]"
        else:
            amap = "1:a"
    elif bgm:
        cmd += ["-stream_loop", "-1", "-i", bgm]
        fc.append(f"[1:a]volume={a.bgm_vol},afade=t=out:st={max(0, total-2):.2f}:d=2[aout]")
        amap = "[aout]"
    if vf:
        fc.append(f"[0:v]{','.join(vf)}[vout]")
    if fc:
        cmd += ["-filter_complex", ";".join(fc)]
    cmd += ["-map", "[vout]" if vf else "0:v"]
    if amap:
        cmd += ["-map", amap]
    cmd += ["-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    run(cmd)

    # ── Lớp ambience liền mạch (keo dán #1) rồi lớp SFX — đều TRƯỚC light để bản nhẹ kế thừa ──
    if a.ambience != "off":
        amb = pdir / "05_audio" / "ambience.mp3" if a.ambience == "auto" else Path(a.ambience)
        if amb.exists():
            apply_ambience_layer(out, amb, a.ambience_vol)
        elif a.ambience != "auto":
            print(f"⚠ không thấy file ambience: {amb}")
    if a.sfx != "off":
        apply_sfx_layer(out, pdir, a.sfx_vol)

    if a.light:
        light = out.with_name(out.stem + "_light" + out.suffix)
        vf = ["-vf", f"scale={a.light_scale}:-2"] if a.light_scale else []
        run(["ffmpeg", "-y", "-v", "error", "-i", str(out), *vf,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", str(a.light_crf),
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(light)])
        print(f"🪶 bản share nhẹ: {light} (CRF {a.light_crf}"
              + (f", rộng {a.light_scale}px" if a.light_scale else "") + ")")

    if ass.exists() and not can_burn:
        import shutil
        shutil.copy(ass, out.parent / ass.name)
        print(f"KIT: base sạch {out} + sub rời {out.parent / ass.name} (burn sau hoặc giao CapCut).")
    print(f"✅ {out} ({total:.1f}s, {w}x{h}, {len(norm)} đoạn)")


if __name__ == "__main__":
    main()

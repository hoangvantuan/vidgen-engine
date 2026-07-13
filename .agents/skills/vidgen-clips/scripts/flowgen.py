#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flowgen.py — CLI gọi flow-agent (omniflash) cho bộ skill vidgen-*.

Ảnh (T2I/I2I) KHÔNG tốn credit — gen thoải mái. Video (I2V/T2V/R2V/FL) TỐN credit.

Subcommands:
  t2i           Gen ảnh từ prompt (kèm --ref media_id để giữ nhất quán nhân vật)
  upload-image  Upload ảnh local → media_id
  clip          Gen 1 clip (mode t2v/i2v/r2v/fl/v2v) + poll + tải + xóa watermark
                (v2v = SỬA clip đã có, khỏi gen lại: --video-id <media_id> hoặc --video-file <local>)
  scene-images  Batch: gen ảnh khung đầu cho các cảnh chưa có ảnh (đọc project.json)
  scene-clips   Batch: I2V các cảnh đã duyệt ảnh, resume theo manifest, retry 1 lần
  compose-frame Composite khung đầu cảnh ĐÔNG thực thể: ghép dần từng nhân vật/prop qua
                nhiều lượt edit ảnh miễn phí (mỗi lượt ≤3 ref, tích lũy) — né giới hạn 3 ref
  extract-chain Trích TRƯỚC khung chain/refprev cho người duyệt (scene-clips dùng lại)
  qc-clips      QC continuity trên CLIP THẬT: frame đầu/giữa/cuối + ledger.md đối chiếu
  compile-prompts  Ghép scenes[].prompt từ field craft (shots[] coverage + props/state)
  qc-storyboard    Đo luật ngữ pháp cảnh + đồng bộ thực thể + state logic — warn-only

Chạy bằng python có deps (websockets, cv2, numpy): ~/.venv/claude/bin/python
Ví dụ:
  PY=~/.venv/claude/bin/python
  $PY flowgen.py t2i --prompt "..." --aspect portrait --out anchor.png
  $PY flowgen.py scene-images --project projects/con-cao
  $PY flowgen.py scene-clips  --project projects/con-cao
"""
from __future__ import annotations

import argparse
import asyncio
import errno
import json
import os
import sys
import tempfile
from pathlib import Path

def _find_flow_agent() -> Path:
    """Tìm repo flow-agent (chứa package omniflash) theo thứ tự:
    env FLOW_AGENT_ROOT → vidgen.config.json ở root engine → chính engine root."""
    env = os.environ.get("FLOW_AGENT_ROOT")
    if env:
        return Path(env)
    engine_root = Path(__file__).resolve().parents[4]
    cfg = engine_root / "vidgen.config.json"
    if cfg.exists():
        root = json.loads(cfg.read_text(encoding="utf-8")).get("flow_agent_root", "")
        if root and (Path(root) / "omniflash").is_dir():
            return Path(root)
    if (engine_root / "omniflash").is_dir():
        return engine_root
    raise SystemExit("Không tìm thấy repo flow-agent (package omniflash). "
                     "Set env FLOW_AGENT_ROOT hoặc ghi vidgen.config.json ở root engine: "
                     '{"flow_agent_root": "/duong/dan/flow-agent"}')


REPO = _find_flow_agent()
sys.path.insert(0, str(REPO))

from omniflash import (  # noqa: E402
    ASPECTS, DEFAULT_PROJECT, ExtensionBridge, download_video, edit_video,
    generate_video, generate_video_i2v, poll_status, upload_image, upload_video,
)
from omniflash.generators.i2v import generate_video_fl, generate_video_r2v  # noqa: E402
from omniflash.generators.t2i import download_image, generate_image  # noqa: E402
from omniflash.watermark import remove_watermark_video  # noqa: E402


# ── manifest ──────────────────────────────────────────────────────────────
def load_manifest(project_dir: Path) -> dict:
    p = project_dir / "project.json"
    if not p.exists():
        raise SystemExit(f"Không thấy manifest: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def save_manifest(project_dir: Path, m: dict):
    """Ghi atomic: hỏng giữa chừng không phá manifest cũ."""
    p = project_dir / "project.json"
    fd, tmp = tempfile.mkstemp(dir=project_dir, suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


# Câu đuôi chống AI tự chèn chữ vào ảnh (T2I hay bịa text/thư pháp/watermark dù không yêu cầu).
NO_TEXT = (", no text, no letters, no words, no captions, no watermark, no signage"
           ", no speech bubbles, no comic dialogue balloons")


def patch_scene(project_dir: Path, scene_id, key: str, value):
    """Re-load manifest từ đĩa, CHỈ set scenes[sid][key]=value rồi ghi atomic.
    Giữ đúng hợp đồng schema (script chỉ đụng field nó sở hữu) → sửa tay giữa chừng không bị đè im lặng."""
    m = load_manifest(project_dir)
    for sc in m.get("scenes", []):
        if sc.get("id") == scene_id:
            sc[key] = value
            break
    save_manifest(project_dir, m)


def patch_shot(project_dir: Path, scene_id, shot_id, key: str, value):
    """Như patch_scene nhưng cho 1 SHOT (workflow v2): chỉ set scenes[sid].shots[shid][key]
    — sửa tay field khác của shot/cảnh giữa batch không bị đè im lặng."""
    m = load_manifest(project_dir)
    for sc in m.get("scenes", []):
        if sc.get("id") == scene_id:
            for sh in sc.get("shots", []):
                if sh.get("id") == shot_id:
                    sh[key] = value
                    break
            break
    save_manifest(project_dir, m)


def _gen_duration(want) -> int:
    """Veo chỉ nhận 4/6/8/10 — chọn mức NHỎ NHẤT ≥ duration shot muốn (thừa sẽ trim khi stitch,
    lấy đoạn ĐẦU — đỉnh chất lượng generation)."""
    w = float(want or 8)
    return next((d for d in (4, 6, 8, 10) if d >= w), 10)


def stitch_shots(pdir: Path, s: dict) -> str | None:
    """SHOT-FIRST: ghép các shot clip của 1 cảnh (trim theo shot.duration, CẮT CỨNG nội cảnh)
    → 04_clips/sceneNN.mp4 ĐÚNG hợp đồng cũ — assemble không cần biết shot tồn tại.
    Trả path hoặc None (thiếu shot chưa done)."""
    import subprocess
    shots = s.get("shots") or []
    parts = []
    for sh in shots:
        cf = (sh.get("clip") or {}).get("file") or f"04_clips/scene{s['id']:02d}_s{sh.get('id')}.mp4"
        p = pdir / cf
        if (sh.get("clip") or {}).get("status") != "done" or not p.exists():
            return None
        parts.append((p, float(sh.get("duration") or 0)))
    out = pdir / "04_clips" / f"scene{s['id']:02d}.mp4"
    inputs, filters = [], []
    for i, (p, dur) in enumerate(parts):
        inputs += ["-i", str(p)]
        trim = f"trim=duration={dur}," if dur > 0 else ""
        filters.append(f"[{i}:v]{trim}setpts=PTS-STARTPTS[v{i}]")
    concat_in = "".join(f"[v{i}]" for i in range(len(parts)))
    graph = ";".join(filters) + f";{concat_in}concat=n={len(parts)}:v=1:a=0[out]"
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", graph, "-map", "[out]",
           "-an", "-c:v", "libx264", "-crf", "18", "-preset", "medium", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ✗ stitch cảnh {s['id']} lỗi ffmpeg: {r.stderr[-300:]}")
        return None
    return str(out.relative_to(pdir))


def _pick_anchor(anchors: list, angle: str):
    """Chọn anchor đúng angle (có media_id), fallback anchor đầu có media_id."""
    return next((a for a in anchors if a.get("angle") == angle and a.get("media_id")),
                next((a for a in anchors if a.get("media_id")), None))


def anchor_ids_for_scene(m: dict, scene: dict, include_location: bool = True) -> list[str]:
    """Gom media_id anchor — tối đa 3 ref/prompt. Thứ tự ưu tiên slot (khán giả bắt lệch MẶT
    nhạy nhất): NHÂN VẬT (theo angle, thứ tự khai = mặt-rõ trước) → HERO-PROP → BỐI CẢNH.
    include_location=False khi cảnh có ref_prev (frame thật cảnh trước THAY location anchor)."""
    ids = []
    chars = {c["id"]: c for c in m.get("characters", [])}
    for cid in scene.get("characters", []):
        c = chars.get(cid)
        if not c:
            continue
        pick = _pick_anchor(c.get("anchors", []), scene.get("angle", "front"))
        if pick:
            ids.append(pick["media_id"])
    props = {p["id"]: p for p in m.get("props", [])}
    for pid in scene.get("props", []) or []:
        p = props.get(pid)
        mid = ((p or {}).get("anchor") or {}).get("media_id")
        if mid and mid not in ids:
            ids.append(mid)
    lid = scene.get("location")
    if lid and include_location:
        loc = next((l for l in m.get("locations", []) if l.get("id") == lid), None)
        if loc:
            pick = _pick_anchor(loc.get("anchors", []), scene.get("location_angle", ""))
            if pick and pick["media_id"] not in ids:
                ids.append(pick["media_id"])
    return ids[:3]


def count_anchor_candidates(m: dict, scene: dict) -> int:
    """Đếm ứng viên CẦN neo của cảnh (nhân vật khai + hero-prop + location) — KHÔNG cắt 3.
    Dùng cho QC: >3 = vượt ngân sách ref → gợi ý đường composite."""
    n = len(scene.get("characters") or [])
    props = {p["id"]: p for p in m.get("props", [])}
    n += sum(1 for pid in scene.get("props") or [] if props.get(pid, {}).get("hero"))
    if scene.get("location"):
        n += 1
    return n


def extract_sharp_end_frame(video_path: str, out_png: str, window: int = 6) -> bool:
    """FRAME-CHAINING: trích frame NÉT nhất trong ~window frame cuối clip → làm khung đầu cảnh sau.
    Khung cuối clip AI hay motion-blur; chọn theo độ nét (Laplacian variance) để nối liền mạch mà
    không bê frame mờ. Dùng cv2 (đã có trong venv). Trả True nếu ghi được ảnh."""
    import cv2  # noqa: PLC0415 — import cục bộ, tránh phụ thuộc khi lệnh khác không cần
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        cap.release()
        return False
    best, best_score = None, -1.0
    for idx in range(max(0, total - window), total):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = float(cv2.Laplacian(gray, cv2.CV_64F).var())  # càng cao càng nét
        if score > best_score:
            best_score, best = score, frame
    cap.release()
    if best is None:
        return False
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(out_png, best)
    return True


def _prev_frame(pdir: Path, prev: dict | None, sid, kind: str):
    """Trích khung cuối NÉT của clip cảnh trước → 03_images/sceneNN_<kind>.png.
    kind: 'chain' (link_prev — làm khung đầu) | 'refprev' (ref_prev — làm reference).
    Trả Path hoặc None (thiếu clip trước)."""
    if not prev:
        return None
    pf = prev.get("clip", {}).get("file") or f"04_clips/scene{prev['id']:02d}.mp4"
    cand = pdir / pf
    if not (cand.exists() and cand.stat().st_size > 0):
        return None
    out = pdir / "03_images" / f"scene{int(sid):02d}_{kind}.png"
    if out.exists() and out.stat().st_size > 0:  # đã trích (extract-chain) → dùng bản đã duyệt
        return out
    return out if extract_sharp_end_frame(str(cand), str(out)) else None


# ── prompt compiler (local, không tốn credit) ─────────────────────────────
# Bảng emotion → recipe. Nguồn: references/emotion-recipe.md (6 công thức gốc CinematicHubClone
# + 2 biến thể suy ra). Field để TRỐNG mới auto-fill; field điền tay luôn thắng.
EMOTION_RECIPE = {
    "fear":      {"camera_angle": "dutch", "shot_size": "close", "lighting": "low_key",
                  "atmosphere": "fog", "kw": "chiaroscuro, ominous shadows, unsettling mood"},
    "joy":       {"camera_angle": "eye_level", "shot_size": "wide", "lighting": "high_key",
                  "atmosphere": "", "kw": "warm, vibrant, airy, clear sunny sky"},
    "sadness":   {"camera_angle": "high", "shot_size": "wide", "lighting": "blue_hour",
                  "atmosphere": "", "kw": "isolated, empty space, melancholic"},
    "power":     {"camera_angle": "low", "shot_size": "medium", "lighting": "rembrandt",
                  "atmosphere": "god_rays", "kw": "imposing, larger than life"},
    "romance":   {"camera_angle": "eye_level", "shot_size": "close", "lighting": "golden_hour",
                  "atmosphere": "", "kw": "warm glow, intimate, shallow depth of field"},
    "chaos":     {"camera_angle": "dutch", "shot_size": "close", "lighting": "low_key",
                  "atmosphere": "dust", "kw": "handheld, disorienting, no stable horizon"},
    "calm":      {"camera_angle": "eye_level", "shot_size": "medium", "lighting": "soft",
                  "atmosphere": "", "kw": "balanced, serene, gentle"},
    "wonder":    {"camera_angle": "low", "shot_size": "establishing", "lighting": "golden_hour",
                  "atmosphere": "god_rays", "kw": "awe, sweeping, luminous"},
}
# Alias cảm xúc → key chuẩn
EMOTION_ALIAS = {"tension": "fear", "loneliness": "sadness", "melancholy": "sadness",
                 "dominance": "power", "intimacy": "romance", "madness": "chaos"}

_ANGLE = {"eye_level": "eye-level shot", "low": "low-angle shot", "high": "high-angle shot",
          "dutch": "dutch angle", "overhead": "overhead shot", "over_shoulder": "over-the-shoulder shot"}
_SHOT = {"wide": "wide shot", "medium": "medium shot", "close": "close-up",
         "extreme_close": "extreme close-up", "establishing": "establishing wide shot"}
_MOVE = {"static": "static camera", "push_in": "slow push-in", "pull_out": "slow pull-out",
         "pan": "smooth pan", "tilt": "smooth tilt", "orbit": "orbiting camera",
         "handheld": "handheld camera", "crane": "crane move"}
_LIGHT = {"high_key": "high-key lighting", "low_key": "low-key lighting", "rembrandt": "Rembrandt lighting",
          "silhouette": "silhouette lighting", "rim": "rim light", "golden_hour": "golden hour light",
          "blue_hour": "blue hour light", "chiaroscuro": "chiaroscuro", "soft": "soft diffused light",
          "hard": "hard directional light"}
_ATMOS = {"rain": "gentle rain", "fog": "foggy atmosphere", "smoke": "thin smoke",
          "god_rays": "volumetric god rays", "dust": "dust in the air", "snow": "falling snow",
          "haze": "hazy air"}
_LENS = {"wide_24": "24mm wide lens", "35mm": "shot on 35mm lens", "50mm": "50mm lens",
         "85mm": "85mm portrait lens", "macro": "macro lens"}
_DIR = {"L2R": "moving left to right", "R2L": "moving right to left",
        "toward": "moving toward camera", "away": "moving away from camera", "static": ""}


def _recipe(emotion):
    e = str(emotion or "")
    return EMOTION_RECIPE.get(EMOTION_ALIAS.get(e, e))


# Thứ tự thời điểm trong ngày (state.time_of_day) — QC đo "thời gian chạy lùi"
TIME_ORDER = ["dawn", "morning", "noon", "afternoon", "dusk", "night"]
_TIME_EN = {"dawn": "at dawn", "morning": "in the morning", "noon": "at midday",
            "afternoon": "in the afternoon", "dusk": "at dusk", "night": "at night"}
# lighting mâu thuẫn hiển nhiên với time_of_day (QC nhóm G — chỉ bắt cặp chắc chắn sai)
_TIME_LIGHT_CLASH = {"night": {"golden_hour", "high_key"}, "noon": {"blue_hour", "golden_hour"},
                     "morning": {"blue_hour"}}


def effective_state(m: dict, s: dict) -> dict:
    """State HIỆU DỤNG của cảnh: time_of_day/weather trống = KẾ THỪA cảnh gần nhất phía trước
    có khai (sổ liên tục — điền 1 lần, các cảnh sau tự theo). Field per-nhân-vật không kế thừa
    (trạng thái đổi theo diễn biến, kế thừa im lặng dễ sai hơn bỏ trống)."""
    eff = dict(s.get("state") or {})
    need = [k for k in ("time_of_day", "weather") if not (eff.get(k) or "").strip()]
    if need:
        scenes = m.get("scenes", [])
        idx = next((i for i, x in enumerate(scenes) if x.get("id") == s.get("id")), -1)
        for prev in reversed(scenes[:max(idx, 0)]):
            st = prev.get("state") or {}
            for k in list(need):
                if (st.get(k) or "").strip():
                    eff[k] = st[k]
                    need.remove(k)
            if not need:
                break
    return eff


def _ts(sec) -> str:
    """Giây → mốc 'MM:SS' cho timestamp prompting."""
    sec = int(sec or 0)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _compile_shots_block(s: dict) -> tuple[str | None, str]:
    """COVERAGE: ghép shots[] thành chuỗi mốc thời gian (timestamp prompting Veo 3.1 —
    nhiều cú cắt xen trong CÙNG 1 generation, nguồn Google Cloud). Thay cho khối
    [Cinematography]+[Action] của cảnh 1-cú. Trả (block|None, note lỗi)."""
    parts, warns = [], []
    for i, sh in enumerate(s.get("shots") or [], 1):
        act = (sh.get("action") or "").strip()
        if not act:
            return None, f"THIẾU LIỆU: shots[{i}] không có 'action'"
        cine = [_SHOT.get(sh.get("shot_size", ""), sh.get("shot_size", "")),
                _ANGLE.get(sh.get("camera_angle", ""), sh.get("camera_angle", "")),
                _MOVE.get(sh.get("camera_move", ""), sh.get("camera_move", ""))]
        cine = ", ".join(x for x in cine if x)
        parts.append(f"[{_ts(sh.get('from'))}-{_ts(sh.get('to'))}] "
                     + (f"{cine}: {act}" if cine else act))
    last_to = (s.get("shots") or [{}])[-1].get("to")
    if last_to and s.get("duration") and int(last_to) > int(s["duration"]):
        warns.append(f"shots vượt duration ({last_to}s > {s['duration']}s)")
    return ". ".join(parts), ("; ".join(warns) if warns else "")


def shot_style(s: dict) -> str:
    """Phân loại shots[]: '' (không có — 1 cú như cũ) | 'timestamp' (from/to — micro-cut
    trong 1 generation) | 'separate' (duration — SHOT-FIRST: mỗi shot 1 generation riêng)."""
    shots = s.get("shots") or []
    if not shots:
        return ""
    return "separate" if any("duration" in sh for sh in shots) else "timestamp"


def compile_shot_prompt(m: dict, s: dict, sh: dict) -> tuple[str | None, str]:
    """SHOT-FIRST: prompt riêng cho 1 shot — cine/action từ SHOT, subject/context/style/state
    từ SCENE (container ngữ nghĩa). Tái dùng compile_scene_prompt qua scene giả lập để 2 đường
    tả MỘT KIỂU (không nhân đôi logic)."""
    pseudo = {k: v for k, v in s.items() if k != "shots"}
    for k in ("shot_size", "camera_angle", "camera_move", "action", "lens", "prompt"):
        pseudo[k] = sh.get(k, "")   # cine/action của SHOT (scene-level bị bỏ qua khi có shots[])
    pseudo["prompt_override"] = bool(sh.get("prompt_override"))
    return compile_scene_prompt(m, pseudo)


def compile_scene_prompt(m: dict, s: dict) -> tuple[str | None, str]:
    """Ghép prompt Veo từ field craft. Trả (prompt|None, note).
    None = bỏ qua (override / thiếu liệu / shot-first). Idempotent, emotion auto-fill field trống.
    shots[] timestamp → chuỗi mốc thay [Cinematography]+[Action]; shots[] separate → cmd compile
    per shot (compile_shot_prompt), prompt cấp scene không dùng."""
    if s.get("prompt_override"):
        return None, "giữ nguyên (prompt_override — prompt viết tay)"
    if shot_style(s) == "separate":
        return None, "__separate__"
    shots = s.get("shots") or []
    action = (s.get("action") or "").strip()
    if not action and not shots:
        # Không có action để ghép. Nếu có prompt tay (dự án Mức 3 cũ) → giữ, đừng xoá.
        if (s.get("prompt") or "").strip():
            return None, "giữ prompt cũ (thiếu 'action'; set prompt_override=true để chốt viết tay)"
        return None, "THIẾU LIỆU: cả 'action' lẫn 'prompt' đều trống — không đủ để ghép"

    rec = _recipe(s.get("emotion", "")) or {}
    def pick(field):  # field tay thắng; trống thì lấy từ recipe theo emotion
        return (s.get(field) or "").strip() or rec.get(field, "")

    shot_size, camera_angle = pick("shot_size"), pick("camera_angle")
    lighting, atmosphere = pick("lighting"), pick("atmosphere")
    camera_move = (s.get("camera_move") or "").strip()
    lens = (s.get("lens") or "").strip()
    sdir = (s.get("screen_direction") or "").strip()

    # [Cinematography] — cảnh coverage (shots[]) tự khai cỡ/góc TỪNG CÚ trong block timestamp,
    # nên bỏ cine/action top-level; chỉ giữ lens + screen_direction áp chung cả generation.
    shots_block, shots_note = (None, "")
    if shots:
        shots_block, shots_note = _compile_shots_block(s)
        if shots_block is None:
            return None, shots_note  # THIẾU LIỆU trong shots[]
        cine = [_LENS.get(lens, lens), _DIR.get(sdir, sdir)]
    else:
        cine = [_SHOT.get(shot_size, shot_size), _ANGLE.get(camera_angle, camera_angle),
                _MOVE.get(camera_move, camera_move), _LENS.get(lens, lens), _DIR.get(sdir, sdir)]
    cine = [x for x in cine if x]

    # [Subject] — nhắc NGUYÊN VĂN desc nhân vật + state THỊ GIÁC (wardrobe/condition/held_props)
    # + desc prop từ registry + thoại trong hình
    chars = {c["id"]: c for c in m.get("characters", [])}
    props = {p["id"]: p for p in m.get("props", [])}
    st = effective_state(m, s)
    subj = []
    for cid in s.get("characters", []):
        if cid not in chars or not chars[cid].get("desc"):
            continue
        bits = [chars[cid]["desc"]]
        for key in ("wardrobe", "condition"):
            v = ((st.get(key) or {}).get(cid) or "").strip()
            if v:
                bits.append(v)
        held = [props[pid]["desc"] for pid in (st.get("held_props") or {}).get(cid, [])
                if pid in props and props[pid].get("desc")]
        if held:
            bits.append("holding " + ", ".join(held))
        subj.append(", ".join(bits))
    for pid in s.get("props", []) or []:  # prop trong khung mà không ai cầm
        if pid in props and props[pid].get("desc") \
                and pid not in {h for hs in (st.get("held_props") or {}).values() for h in hs}:
            subj.append(props[pid]["desc"])
    # Pipeline LỒNG TIẾNG (bỏ audio Veo, không khớp miệng) → KHÔNG nhét câu thoại literal vào
    # prompt: chữ nước ngoài khiến model vẽ BONG BÓNG THOẠI/chữ trong hình (bài học akasto).
    # Chỉ phát tín hiệu "đang nói" TRUNG TÍNH cho khẩu hình động; lời thật do tts_to_ass.py đọc.
    if s.get("dialogue"):
        subj.append("the character is speaking warmly, mouth gently open mid-word, expressive face")

    # [Context] — khoá bối cảnh: lặp nguyên văn desc location
    locs = {l["id"]: l for l in m.get("locations", [])}
    context = ""
    lid = s.get("location")
    if lid and lid in locs and locs[lid].get("desc"):
        context = locs[lid]["desc"]

    # [Style & Ambiance] — style chung dự án + thời điểm/thời tiết (state) + ánh sáng + atmosphere
    # + keyword emotion + sfx
    amb = [m.get("style", "").strip(),
           _TIME_EN.get((st.get("time_of_day") or "").strip(), (st.get("time_of_day") or "").strip()),
           (st.get("weather") or "").strip() and f"{st['weather'].strip()} weather" or "",
           _LIGHT.get(lighting, lighting), _ATMOS.get(atmosphere, atmosphere),
           rec.get("kw", "")]
    for fx in s.get("sfx", []) or []:
        if (fx or "").strip():
            amb.append(f"audible {fx.strip()}")
    amb = [x for x in amb if x]

    parts = []
    if shots_block:
        # Coverage: thiết lập chung (subject + context) TRƯỚC, rồi chuỗi mốc cắt xen, cuối style.
        if subj:    parts.append(", ".join(subj))
        if context: parts.append(context)
        if cine:    parts.append(", ".join(cine))
        parts.append(shots_block)
        if amb:     parts.append(", ".join(amb))
    else:
        if cine:    parts.append(", ".join(cine))
        if subj:    parts.append(", ".join(subj))
        parts.append(action)
        if context: parts.append(context)
        if amb:     parts.append(", ".join(amb))
    prompt = ". ".join(p.rstrip(". ") for p in parts if p) + "."
    fill_fields = ("lighting", "atmosphere") if shots else \
        ("shot_size", "camera_angle", "lighting", "atmosphere")  # shots[]: cỡ/góc per-cú, không auto-fill
    filled = [f for f in fill_fields if not (s.get(f) or "").strip() and rec.get(f)]
    note = "compiled" + (f" (coverage {len(shots)} cú)" if shots else "") \
        + (f" (emotion auto-fill: {', '.join(filled)})" if filled else "") \
        + (f" ⚠ {shots_note}" if shots_note else "")
    return prompt, note


async def cmd_compile_prompts(a):  # async để khớp dispatch asyncio.run; thân thuần local, không await
    pdir = Path(a.project)
    m = load_manifest(pdir)
    # element_lock=false TƯỜNG MINH (dự án v2) → storyboard chưa được duyệt bảng element.
    # Dự án cũ thiếu key → coi như mở (backward-compat).
    if m.get("gates", {}).get("element_lock") is False and not a.dry_run:
        raise SystemExit("GATE 1A2 (element_lock) chưa mở — duyệt bảng element "
                         "(01_script/elements.md) trước khi compile. Xem trước: --dry-run.")
    changed, skipped, warned = [], [], []
    for s in m.get("scenes", []):
        if a.scene and s["id"] not in a.scene:
            continue
        # SHOT-FIRST: compile per shot, prompt cấp scene không dùng
        if shot_style(s) == "separate":
            for sh in s["shots"]:
                p_sh, n_sh = compile_shot_prompt(m, s, sh)
                sid_lbl = f"{s['id']}.s{sh.get('id', '?')}"
                if p_sh is None:
                    (warned if n_sh.startswith("THIẾU") else skipped).append((sid_lbl, n_sh))
                    continue
                sh["prompt"] = p_sh
                changed.append((sid_lbl, n_sh))
                print(f"— Shot {sid_lbl}: {n_sh}\n    {p_sh}")
            continue
        prompt, note = compile_scene_prompt(m, s)
        if prompt is None:
            (warned if note.startswith("THIẾU") else skipped).append((s["id"], note))
            continue
        s["prompt"] = prompt
        changed.append((s["id"], note))
        print(f"— Cảnh {s['id']}: {note}\n    {prompt}")
    if not a.dry_run and changed:
        save_manifest(pdir, m)  # ghi atomic toàn manifest (đã cập nhật prompt các cảnh)
    print(f"\nCompiled {len(changed)} | giữ nguyên {len(skipped)} | THIẾU LIỆU {len(warned)}"
          + (" (DRY-RUN, chưa ghi)" if a.dry_run else ""))
    for sid, note in warned:
        print(f"  ⚠ cảnh {sid}: {note}")


# ── QC storyboard (local, warn-only) ──────────────────────────────────────
# Đo các luật ngữ pháp cảnh ĐO ĐƯỢC (scene-grammar.md §7): đơn điệu nhịp/góc/cỡ, transition
# đồng loạt, thiếu re-establish, field continuity mồ côi, beat đắt chưa coverage, VO lệch nhịp.
# WARN-ONLY: luật điện ảnh là mặc-định-để-phá-có-chủ-đích — máy đo, NGƯỜI quyết ở GATE 1B.
# Ra đời từ bài học dự án thật đầu tiên: 15/15 cảnh 8.0s, 8 cảnh liền high-angle, 67% fade,
# 0 link — mọi guidance chữ đều có sẵn mà không giữ được; chỉ cái ĐO ĐƯỢC mới thành kỷ luật.

_ANGLE_RX = [  # regex prompt → key chuẩn (dự án cũ prompt tay: góc chôn trong text vẫn đo được)
    ("over_shoulder", r"over[- ]the[- ]shoulder"), ("overhead", r"overhead|bird'?s[- ]eye|top[- ]down"),
    ("dutch", r"dutch"), ("low", r"low[- ]angle|worm'?s[- ]eye"), ("high", r"high[- ]angle|aerial"),
    ("eye_level", r"eye[- ]level"),
]
_SHOT_RX = [
    ("extreme_close", r"extreme close[- ]up|macro"), ("close", r"close[- ]up"),
    ("establishing", r"establishing"), ("wide", r"wide shot|wide[- ]angle|long shot"),
    ("medium", r"medium shot"),
]
_SOFT_TRANS = {"fade", "dissolve", "fadewhite", "fadeblack", "wipeleft", "wiperight",
               "slideleft", "slideright", "circleopen", "circleclose"}


def _rx_pick(text: str, table) -> str:
    import re
    for key, rx in table:
        if re.search(rx, text, re.IGNORECASE):
            return key
    return ""


def _effective(s: dict, field: str, rx_table) -> str:
    """Giá trị HIỆU DỤNG của field: điền tay → auto-fill emotion → mò trong prompt (dự án cũ)."""
    v = (s.get(field) or "").strip()
    if v:
        return v
    rec = _recipe(s.get("emotion", "")) or {}
    if rec.get(field):
        return rec[field]
    return _rx_pick(s.get("prompt") or "", rx_table)


def _runs(values):
    """Gom chuỗi giá trị TRÙNG liên tiếp → list (giá trị, [ids]). Giá trị rỗng phá chuỗi."""
    out = []
    for sid, v in values:
        if v and out and out[-1][0] == v:
            out[-1][1].append(sid)
        else:
            out.append([v, [sid]])
    return [(v, ids) for v, ids in out if v]


async def cmd_qc_storyboard(a):  # async khớp dispatch; thân thuần local
    pdir = Path(a.project)
    m = load_manifest(pdir)
    scenes = m.get("scenes", [])
    if not scenes:
        print("Manifest không có cảnh nào.")
        return
    W, I = [], []  # (nhóm, msg) — ⚠ warn / ℹ info

    # A · NHỊP — duration phải biến thiên theo beat
    durs = [(s["id"], s.get("duration", 8)) for s in scenes]
    if len({d for _, d in durs}) == 1 and len(durs) >= 4:
        W.append(("NHỊP", f"CẢ {len(durs)} cảnh cùng duration {durs[0][1]}s — chữ ký slideshow. "
                          "Biến thiên theo beat: căng 4-6s, ngấm 8-10s, cao trào ngắn dần."))
    else:
        for v, ids in _runs(durs):
            if len(ids) >= 4:
                W.append(("NHỊP", f"cảnh {ids[0]}–{ids[-1]}: {len(ids)} cảnh liền cùng {v}s — "
                                  "nhịp đều, cân nhắc đổi (trừ khi chủ đích, vd ru ngủ)."))

    # B · GÓC/CỠ — chuỗi trùng liên tiếp (điểm nhìn trôi vô thức)
    for field, rx, label, lim in (("camera_angle", _ANGLE_RX, "GÓC MÁY", 3),
                                  ("shot_size", _SHOT_RX, "CỠ CẢNH", 3)):
        vals = [(s["id"], _effective(s, field, rx)) for s in scenes]
        for v, ids in _runs(vals):
            if len(ids) >= lim:
                W.append((label, f"cảnh {ids[0]}–{ids[-1]}: {len(ids)} cảnh liền cùng '{v}' — "
                                 "đổi góc/cỡ hoặc ghi lý do trục điểm nhìn vào kichban.md."))

    # C · CHUYỂN CẢNH — transition mềm đồng loạt (cut là mặc định phim, không warn)
    trans = [((s.get("transition") or {}).get("type") or "cut") for s in scenes[:-1]]
    if trans:
        from collections import Counter
        top, n = Counter(trans).most_common(1)[0]
        if top in _SOFT_TRANS and n / len(trans) > 0.6:
            W.append(("CHUYỂN CẢNH", f"'{top}' chiếm {n}/{len(trans)} ({n * 100 // len(trans)}%) — "
                                     "transition mềm là dấu câu mang nghĩa, mặc định nên là cut."))

    # D · CONTINUITY/COVERAGE — re-establish, field mồ côi, beat đắt chưa cover
    prev = None
    for s in scenes:
        loc = s.get("location")
        if loc and prev is not None and loc != prev.get("location"):
            eff = _effective(s, "shot_size", _SHOT_RX)
            if eff not in ("wide", "establishing"):
                verb = "vào location mới" if prev.get("location") else "quay lại location"
                W.append(("CONTINUITY", f"cảnh {s['id']}: {verb} '{loc}' bằng '{eff or '?'}' — "
                                        "nên wide/establishing (re-establish) trừ khi phá có chủ đích."))
        if prev is not None and loc and loc == prev.get("location"):
            shared = set(prev.get("characters") or []) & set(s.get("characters") or [])
            linked = s.get("link_prev") or s.get("match_cut_with") is not None \
                or prev.get("match_cut_with") is not None
            if shared and not linked:
                I.append(("CONTINUITY", f"cảnh {prev['id']}→{s['id']}: cùng location + nhân vật mà "
                                        "không link_prev/match_cut — ứng viên nối (scene-grammar §7)."))
        if (s.get("role") in ("hook", "turn", "payoff") or s.get("dialogue")) and not s.get("shots"):
            I.append(("COVERAGE", f"cảnh {s['id']} (role={s.get('role') or 'thoại'}): beat đắt chưa có "
                                  "shots[] — cân nhắc coverage 2-3 cú (scene-grammar §6a)."))
        prev = s

    # E · shots[] hợp lệ (2 style) + VO khớp nhịp đọc (~3-4 chữ/giây)
    for s in scenes:
        style = shot_style(s)
        shots = s.get("shots") or []
        if style == "separate":
            # SHOT-FIRST: mỗi shot 1 generation — luật master + duration khớp cảnh
            if any("from" in sh or "to" in sh for sh in shots):
                W.append(("SHOTS", f"cảnh {s['id']}: TRỘN style (vừa duration vừa from/to) — "
                                   "chọn 1: separate (duration) hoặc timestamp (from/to)."))
            if len(shots) >= 2:
                first_sz = (shots[0].get("shot_size") or "").strip()
                if first_sz not in ("wide", "establishing"):
                    W.append(("SHOTS", f"cảnh {s['id']}: shot đầu '{first_sz or '?'}' không phải "
                                       "wide/establishing — cảnh ≥2 shot cần MASTER thiết lập "
                                       "không gian (shot con derive từ nó)."))
            for sh in shots:
                if not (sh.get("action") or "").strip():
                    W.append(("SHOTS", f"cảnh {s['id']} shot {sh.get('id', '?')}: thiếu 'action'."))
                d = float(sh.get("duration") or 0)
                if d and not (1.5 <= d <= 10):
                    I.append(("SHOTS", f"cảnh {s['id']} shot {sh.get('id', '?')}: {d}s — "
                                       "shot thường 2-8s (long-take tối đa 10s)."))
            total = sum(float(sh.get("duration") or 0) for sh in shots)
            if s.get("duration") and abs(total - float(s["duration"])) > 2:
                W.append(("SHOTS", f"cảnh {s['id']}: tổng shot {total:g}s lệch duration cảnh "
                                   f"{s['duration']}s >2s — VO sẽ bị kéo/nén khi ráp."))
        elif style == "timestamp":
            for i, sh in enumerate(shots, 1):
                f, t = sh.get("from", 0), sh.get("to", 0)
                if t <= f:
                    W.append(("SHOTS", f"cảnh {s['id']} shots[{i}]: from/to không tăng ({f}→{t})."))
                elif not (1.5 <= t - f <= 4.5):
                    I.append(("SHOTS", f"cảnh {s['id']} shots[{i}]: cú {t - f}s — nên 2-4s/cú."))
            last = (shots or [{}])[-1].get("to")
            if last and last > s.get("duration", 8):
                W.append(("SHOTS", f"cảnh {s['id']}: shots kết ở {last}s > duration {s.get('duration', 8)}s."))
        vo = (s.get("vo") or "").strip()
        if vo:
            rate = len(vo.split()) / max(1, s.get("duration", 8))
            if rate > 5:
                W.append(("VO", f"cảnh {s['id']}: {len(vo.split())} chữ / {s.get('duration', 8)}s "
                                f"(~{rate:.1f} chữ/s) — VO dài quá, clip sẽ bị kéo chậm lộ trôi nổi."))
            elif rate < 2:
                I.append(("VO", f"cảnh {s['id']}: VO thưa (~{rate:.1f} chữ/s) — chủ đích lặng thì OK."))

    # F · ĐỒNG BỘ THỰC THỂ — mọi thứ lặp lại phải có nguồn sự thật + anchor; vượt 3 ref → composite
    char_reg = {c["id"]: c for c in m.get("characters", [])}
    prop_reg = {p["id"]: p for p in m.get("props", [])}
    for s in scenes:
        for cid in s.get("characters") or []:
            if cid not in char_reg:
                W.append(("THỰC THỂ", f"cảnh {s['id']}: nhân vật '{cid}' KHÔNG có trong characters[] "
                                      "— mỗi generation Veo sẽ tự bịa một người khác."))
        for pid in s.get("props") or []:
            if pid not in prop_reg:
                W.append(("THỰC THỂ", f"cảnh {s['id']}: prop '{pid}' không có trong props[] registry."))
        n = count_anchor_candidates(m, s)
        if n > 3 and not s.get("composite"):
            W.append(("THỰC THỂ", f"cảnh {s['id']}: {n} ứng viên neo > ngân sách 3 ref — bật "
                                  "composite:true (compose-frame) hoặc bớt thực thể/né mặt."))
        elif s.get("composite") and n <= 3:
            I.append(("THỰC THỂ", f"cảnh {s['id']}: composite bật nhưng chỉ {n} ứng viên neo — "
                                  "đường ref thường là đủ."))
        if s.get("ref_prev") and s.get("mode", "i2v") != "r2v":
            W.append(("THỰC THỂ", f"cảnh {s['id']}: ref_prev chỉ có nghĩa với mode r2v "
                                  f"(đang '{s.get('mode', 'i2v')}'); liền mạch thì dùng link_prev."))
        if s.get("ref_prev") and s.get("link_prev"):
            W.append(("THỰC THỂ", f"cảnh {s['id']}: ref_prev + link_prev cùng lúc — chọn 1 "
                                  "(liền mạch = link_prev; đổi góc cùng không gian = ref_prev)."))
        # nhân vật MỒ CÔI: danh từ người trong action/prompt mà không khai characters[]
        import re
        text = (s.get("action") or "") + " " + ((s.get("prompt") or "") if s.get("prompt_override") else "")
        for sh in s.get("shots") or []:
            text += " " + (sh.get("action") or "")
        crowd = sorted(set(re.findall(r"\b(crowd|villagers|people|bystanders)\b", text, re.I)))
        humans = sorted(set(w.lower() for w in re.findall(
            r"\b(?:mother|father|grandma|grandmother|grandpa|grandfather|woman|man|boy|girl|child|children|kids|baby|farmer|soldier|merchant|neighbor)\b",
            text, re.I)))
        # danh từ đã được COVER bởi desc nhân vật khai trong cảnh (vd "girl" nằm trong desc bé) → không mồ côi
        covered = " ".join(char_reg.get(cid, {}).get("desc", "")
                           for cid in s.get("characters") or []).lower()
        humans = [w for w in humans if w not in covered]
        if humans:
            declared = ", ".join(s.get("characters") or []) or "KHÔNG AI"
            W.append(("THỰC THỂ", f"cảnh {s['id']}: action nhắc người ({', '.join(humans)}) nhưng "
                                  f"characters chỉ khai [{declared}] — nhân vật mồ côi sẽ đổi mặt "
                                  "mỗi generation; thêm entry+anchor hoặc viết né mặt."))
        if crowd:
            I.append(("THỰC THỂ", f"cảnh {s['id']}: đám đông ({', '.join(crowd)}) — không anchor được, "
                                  "viết né mặt: turned away / silhouette / out of focus."))
        if s.get("props") and not s.get("composite"):
            heroes = [pid for pid in s["props"] if prop_reg.get(pid, {}).get("hero")]
            no_anchor = [pid for pid in heroes if not (prop_reg[pid].get("anchor") or {}).get("file")]
            if no_anchor:
                W.append(("THỰC THỂ", f"cảnh {s['id']}: hero-prop {no_anchor} chưa có ảnh anchor "
                                      "(T2I miễn phí — gen ở stage character)."))

    # G · STATE/LOGIC XUYÊN CẢNH — chỉ kích hoạt khi dự án có dùng state (backward-compat)
    if any(s.get("state") for s in scenes):
        prev_t = None
        for s in scenes:
            st = effective_state(m, s)
            t = (st.get("time_of_day") or "").strip()
            if t and t not in TIME_ORDER:
                W.append(("STATE", f"cảnh {s['id']}: time_of_day '{t}' lạ — dùng {'/'.join(TIME_ORDER)}."))
            elif t:
                if prev_t and TIME_ORDER.index(t) < TIME_ORDER.index(prev_t):
                    W.append(("STATE", f"cảnh {s['id']}: thời gian chạy LÙI ({prev_t} → {t}) — "
                                       "qua ngày mới/flashback thì ghi chú kichban.md, không thì sửa."))
                prev_t = t
                light = (s.get("lighting") or "").strip() or (_recipe(s.get("emotion", "")) or {}).get("lighting", "")
                if light in _TIME_LIGHT_CLASH.get(t, ()):
                    W.append(("STATE", f"cảnh {s['id']}: lighting '{light}' mâu thuẫn time_of_day "
                                       f"'{t}' — ánh sáng sẽ trôi giữa các cảnh."))
            sst = s.get("state") or {}
            declared = set(s.get("characters") or [])
            for key in ("wardrobe", "condition", "held_props"):
                for cid in (sst.get(key) or {}):
                    if cid not in declared:
                        W.append(("STATE", f"cảnh {s['id']}: state.{key} khai '{cid}' nhưng nhân vật "
                                           "không có trong cảnh — sổ liên tục lệch."))
            for cid, pids in (sst.get("held_props") or {}).items():
                for pid in pids:
                    if pid not in prop_reg:
                        W.append(("STATE", f"cảnh {s['id']}: held_props trỏ prop '{pid}' không có registry."))
            if (s.get("characters") and not sst
                    and any(x.get("state") for x in scenes[:scenes.index(s)])):
                I.append(("STATE", f"cảnh {s['id']}: sổ liên tục ĐỨT (cảnh trước có state, cảnh này "
                                   "trống) — time_of_day/weather vẫn kế thừa, wardrobe/condition thì không."))

    if m.get("gates", {}).get("element_lock") is False:
        W.append(("GATE", "element_lock (GATE 1A2) chưa mở — bảng element phải được duyệt "
                          "TRƯỚC storyboard; compile sẽ chặn khi ghi thật."))

    for tag, items in (("⚠", W), ("ℹ", I)):
        for group, msg in items:
            print(f"{tag} [{group}] {msg}")
    print(f"\nQC storyboard: {len(W)} cảnh báo, {len(I)} gợi ý — WARN-ONLY, người quyết ở GATE 1B."
          f"\nLuật + cách phá có chủ đích: vidgen-script/references/scene-grammar.md")


# ── bridge ────────────────────────────────────────────────────────────────
async def open_bridge(timeout: int = 90) -> ExtensionBridge:
    bridge = ExtensionBridge()
    try:
        await bridge.start()
    except OSError as e:
        if e.errno == errno.EADDRINUSE or "address already in use" in str(e).lower():
            raise SystemExit(
                "Port bridge (8100/9222) đang BẬN — thường do 'python -m cli.api' hoặc flowgen cũ "
                "còn treo. Tắt rồi chạy lại: lsof -nP -iTCP:8100 -sTCP:LISTEN → kill <pid>.")
        raise
    await bridge.wait_for_extension(timeout)
    return bridge


async def gen_and_fetch_clip(bridge, mode: str, prompt: str, aspect_key: str,
                             duration: int, out_path: str, *, image_id=None,
                             end_id=None, ref_ids=None, video_id=None,
                             project_id=DEFAULT_PROJECT, clean: bool = True):
    """Gen 1 clip theo mode, poll tới xong, tải về, xóa watermark. Trả path hoặc None."""
    aspect = ASPECTS.get(aspect_key, aspect_key)
    if mode == "i2v":
        mids = await generate_video_i2v(bridge, prompt, aspect, project_id,
                                        image_media_id=image_id, duration=duration)
    elif mode == "fl":
        mids = await generate_video_fl(bridge, prompt, aspect, project_id,
                                       start_image_id=image_id, end_image_id=end_id,
                                       duration=duration)
    elif mode == "r2v":
        mids = await generate_video_r2v(bridge, prompt, aspect, project_id,
                                        ref_media_ids=ref_ids or [], duration=duration)
    elif mode == "v2v":
        mids = await edit_video(bridge, prompt, aspect, project_id,
                                video_media_id=video_id, duration=duration)
    else:  # t2v
        mids = await generate_video(bridge, prompt, aspect, project_id,
                                    duration=duration, count=1)
    if not mids:
        return None
    mid = mids[0]
    if not await poll_status(bridge, mid, project_id):
        return None
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = str(out.with_name(out.stem + "_raw" + out.suffix))
    if not await download_video(bridge, mid, raw):
        return None
    if clean:
        remove_watermark_video(raw, str(out))
        os.remove(raw)
    else:
        os.replace(raw, str(out))
    return mid


# ── subcommands ───────────────────────────────────────────────────────────
async def cmd_t2i(a):
    bridge = await open_bridge()
    try:
        results = await generate_image(bridge, a.prompt, a.aspect, a.project_id,
                                       count=a.count, ref_media_ids=a.ref or None)
        if not results:
            raise SystemExit("Gen ảnh thất bại.")
        saved = []
        for i, r in enumerate(results):
            out = a.out if a.count == 1 else str(Path(a.out).with_stem(Path(a.out).stem + f"_{i+1}"))
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            ok = await download_image(bridge, r["image_url"], out)
            saved.append({"file": out if ok else None, "media_id": r["media_id"]})
        print(json.dumps(saved, ensure_ascii=False))
    finally:
        await bridge.close()


async def cmd_upload_image(a):
    bridge = await open_bridge()
    try:
        mid = await upload_image(bridge, a.path, a.project_id)
        if not mid:
            raise SystemExit("Upload thất bại.")
        print(json.dumps({"file": a.path, "media_id": mid}, ensure_ascii=False))
    finally:
        await bridge.close()


async def cmd_clip(a):
    bridge = await open_bridge()
    try:
        video_id = a.video_id
        if a.mode == "v2v" and not video_id:
            if not a.video_file:
                raise SystemExit("Mode v2v cần --video-id (media_id có sẵn) hoặc --video-file (upload local).")
            data = await upload_video(a.video_file, a.project_id, bridge)
            video_id = (data.get("mediaId") or data.get("name")
                        or (data.get("media") or {}).get("name"))
            if not video_id:
                raise SystemExit("Upload video thất bại — không lấy được media_id.")
        mid = await gen_and_fetch_clip(
            bridge, a.mode, a.prompt, a.aspect, a.duration, a.out,
            image_id=a.image_id, end_id=a.end_id, ref_ids=a.ref, video_id=video_id,
            project_id=a.project_id, clean=not a.no_clean)
        if not mid:
            raise SystemExit("Gen clip thất bại.")
        print(json.dumps({"file": a.out, "media_id": mid}, ensure_ascii=False))
    finally:
        await bridge.close()


async def cmd_scene_images(a):
    pdir = Path(a.project)
    m = load_manifest(pdir)
    aspect = m.get("aspect", "portrait")
    pid_flow = m.get("flow_project_id") or DEFAULT_PROJECT

    async def gen_one(bridge, prompt: str, refs, out: Path):
        """Gen 1 ảnh + tải về. Trả media_id hoặc None."""
        results = await generate_image(bridge, prompt + ("" if a.allow_text else NO_TEXT),
                                       aspect, pid_flow, count=a.count,
                                       ref_media_ids=refs or None)
        if not results:
            return None
        out.parent.mkdir(parents=True, exist_ok=True)
        await download_image(bridge, results[0]["image_url"], str(out))
        return results[0]["media_id"]

    todo = [s for s in m["scenes"]
            if (not a.scene or s["id"] in a.scene)
            and (s.get("mode", "i2v") in ("i2v", "fl") or shot_style(s) == "separate")]
    bridge = await open_bridge()
    try:
        did = 0
        for s in todo:
            # ── SHOT-FIRST: ảnh khung đầu TỪNG SHOT — MASTER trước, shot con derive ──
            if shot_style(s) == "separate":
                shots = s["shots"]
                master = shots[0]
                m_img = master.get("image") or {}
                if not (m_img.get("media_id") and m_img.get("approved")):
                    if m_img.get("media_id") and not m_img.get("approved"):
                        print(f"— Cảnh {s['id']}: ảnh MASTER (shot {master.get('id')}) chờ duyệt "
                              "— duyệt xong chạy lại để gen shot con (derive cần master).")
                        continue
                    out = pdir / "03_images" / f"scene{s['id']:02d}_s{master.get('id')}.png"
                    print(f"— Cảnh {s['id']} shot {master.get('id')} [MASTER]: gen ảnh")
                    mid = await gen_one(bridge, master.get("prompt") or s.get("prompt") or "",
                                        anchor_ids_for_scene(m, s), out)
                    if mid:
                        patch_shot(pdir, s["id"], master.get("id"),
                                   "image", {"file": str(out.relative_to(pdir)),
                                             "media_id": mid, "approved": False})
                        did += 1
                        print(f"  → duyệt MASTER trước, rồi chạy lại gen shot con.")
                    else:
                        print(f"  ✗ shot master gen lỗi — chạy lại sau.")
                    continue
                # master đã duyệt → derive các shot con: ref = frame MASTER + anchor nhân vật
                for sh in shots[1:]:
                    img = sh.get("image") or {}
                    if img.get("media_id") and img.get("approved"):
                        continue
                    out = pdir / "03_images" / f"scene{s['id']:02d}_s{sh.get('id')}.png"
                    refs = ([m_img["media_id"]]
                            + anchor_ids_for_scene(m, s, include_location=False))[:3]
                    print(f"— Cảnh {s['id']} shot {sh.get('id')} [derive←master]: gen ảnh")
                    mid = await gen_one(bridge, sh.get("prompt") or "", refs, out)
                    if mid:
                        patch_shot(pdir, s["id"], sh.get("id"),
                                   "image", {"file": str(out.relative_to(pdir)),
                                             "media_id": mid, "approved": False})
                        did += 1
                    else:
                        print(f"  ✗ shot {sh.get('id')} gen lỗi — chạy lại sau.")
                continue
            # ── đường cũ: 1 ảnh cấp scene ──
            if s.get("image", {}).get("media_id") and s["image"].get("approved"):
                continue
            out = pdir / "03_images" / f"scene{s['id']:02d}.png"
            refs = anchor_ids_for_scene(m, s)
            print(f"— Cảnh {s['id']}: gen ảnh (refs={len(refs)})")
            mid = await gen_one(bridge, s["prompt"], refs, out)
            if not mid:
                print(f"  ✗ cảnh {s['id']} gen ảnh lỗi — bỏ qua, chạy lại sau.")
                continue
            patch_scene(pdir, s["id"], "image",
                        {"file": str(out.relative_to(pdir)), "media_id": mid, "approved": False})
            did += 1
        print(f"Xong ({did} ảnh). Duyệt trong 03_images/ rồi set image.approved=true "
              "(per shot với cảnh shot-first) trước khi scene-clips.")
    finally:
        await bridge.close()


async def cmd_scene_clips(a):
    pdir = Path(a.project)
    m = load_manifest(pdir)
    if not m.get("gates", {}).get("character_lock") and not a.force:
        raise SystemExit("Gate 2 (character_lock) chưa mở — duyệt anchor + clip thử trước, "
                         "hoặc chạy với --force nếu cố ý.")
    prev_of = {m["scenes"][i]["id"]: (m["scenes"][i - 1] if i > 0 else None)
               for i in range(len(m["scenes"]))}  # cảnh liền trước theo thứ tự manifest (cho frame-chain)
    todo = []
    for s in m["scenes"]:
        if a.scene and s["id"] not in a.scene:
            continue
        if s.get("clip", {}).get("status") == "done" and not a.regen:
            continue
        if shot_style(s) == "separate":  # shot-first: điều kiện kiểm per shot ở vòng gen
            todo.append(s)
            continue
        mode = s.get("mode", "i2v")
        # link_prev lấy khung từ cảnh trước → KHÔNG cần ảnh riêng đã duyệt
        if mode in ("i2v", "fl") and not s.get("link_prev") and not s.get("image", {}).get("approved"):
            print(f"— Cảnh {s['id']}: ảnh chưa duyệt, bỏ qua.")
            continue
        todo.append(s)
    if not todo:
        print("Không có cảnh nào cần gen clip.")
        return
    chained = [s["id"] for s in todo if s.get("link_prev")]
    print(f"Sẽ gen {len(todo)} clip (TỐN credit). Resume: cảnh done sẽ không gen lại."
          + (f" Frame-chain (tuần tự): {chained}" if chained else ""))
    bridge = await open_bridge()
    try:
        for s in todo:
            # ── SHOT-FIRST: clip TỪNG SHOT (i2v từ ảnh shot đã duyệt) rồi STITCH về sceneNN.mp4 ──
            if shot_style(s) == "separate":
                pid_flow = m.get("flow_project_id") or DEFAULT_PROJECT
                for sh in s["shots"]:
                    clip = sh.get("clip") or {}
                    if clip.get("status") == "done" and not a.regen:
                        continue
                    img = sh.get("image") or {}
                    if not (img.get("media_id") and img.get("approved")):
                        print(f"— Cảnh {s['id']} shot {sh.get('id')}: ảnh chưa duyệt, bỏ qua.")
                        continue
                    sout = pdir / "04_clips" / f"scene{s['id']:02d}_s{sh.get('id')}.mp4"
                    gdur = _gen_duration(sh.get("duration"))
                    mid = None
                    for attempt in (1, 2):
                        print(f"— Cảnh {s['id']} shot {sh.get('id')} [i2v {gdur}s] lần {attempt}…")
                        mid = await gen_and_fetch_clip(bridge, "i2v", sh.get("prompt") or "",
                                                       m.get("aspect", "portrait"), gdur,
                                                       str(sout), image_id=img["media_id"],
                                                       project_id=pid_flow)
                        if mid:
                            break
                    patch_shot(pdir, s["id"], sh.get("id"), "clip",
                               {"file": str(sout.relative_to(pdir)), "media_id": mid,
                                "status": "done" if mid else "failed"})
                    sh["clip"] = {"file": str(sout.relative_to(pdir)), "media_id": mid,
                                  "status": "done" if mid else "failed"}
                    print(f"  {'✓' if mid else '✗ FAILED (gen lại: --scene ' + str(s['id']) + ' --regen)'}")
                stitched = stitch_shots(pdir, s)
                if stitched:
                    new_clip = {"file": stitched, "media_id": "", "status": "done"}
                    s["clip"] = new_clip
                    patch_scene(pdir, s["id"], "clip", new_clip)
                    print(f"— Cảnh {s['id']}: ⧉ stitch {len(s['shots'])} shot → {stitched}")
                else:
                    print(f"— Cảnh {s['id']}: chưa stitch (còn shot thiếu/failed).")
                continue
            mode = s.get("mode", "i2v")
            out = pdir / "04_clips" / f"scene{s['id']:02d}.mp4"
            kwargs = dict(project_id=m.get("flow_project_id") or DEFAULT_PROJECT)
            if mode in ("i2v", "fl"):
                kwargs["image_id"] = s.get("image", {}).get("media_id")
            if mode == "fl":
                kwargs["end_id"] = s.get("end_image", {}).get("media_id")
            if mode == "r2v":
                # ── REF_PREV: frame cuối nét cảnh trước làm 1 REF, THAY location anchor ──
                # (danh tính vẫn từ anchor GỐC — chống trôi photocopy; frame mang vai không gian)
                if s.get("ref_prev"):
                    refs = anchor_ids_for_scene(m, s, include_location=False)
                    fp = _prev_frame(pdir, prev_of.get(s["id"]), s["id"], "refprev")
                    fid = await upload_image(bridge, str(fp), kwargs["project_id"]) if fp else None
                    if fid:
                        refs = (refs + [fid])[:3]
                        print(f"— Cảnh {s['id']}: ref_prev — frame cảnh trước thay location anchor.")
                    else:
                        refs = anchor_ids_for_scene(m, s)  # fallback: đủ bộ anchor như thường
                        print(f"— Cảnh {s['id']}: ref_prev fail (thiếu clip trước) → dùng anchor thường.")
                    kwargs["ref_ids"] = refs
                else:
                    kwargs["ref_ids"] = anchor_ids_for_scene(m, s)
            # ── FRAME-CHAINING: khung cuối NÉT của cảnh trước → khung đầu cảnh này ──
            if s.get("link_prev") and mode in ("i2v", "fl"):
                frame_png = pdir / "03_images" / f"scene{s['id']:02d}_chain.png"
                if frame_png.exists() and frame_png.stat().st_size > 0:
                    # đã trích sẵn bằng extract-chain (LUẬT: người duyệt khung chain trước khi đốt credit)
                    cf = await upload_image(bridge, str(frame_png), kwargs["project_id"])
                else:
                    fp = _prev_frame(pdir, prev_of.get(s["id"]), s["id"], "chain")
                    cf = await upload_image(bridge, str(fp), kwargs["project_id"]) if fp else None
                    if cf:
                        print(f"  ⚠ khung chain trích tự động CHƯA qua duyệt ({frame_png.name}) — "
                              "lần sau chạy 'extract-chain' + duyệt trước khi scene-clips.")
                if cf:
                    kwargs["image_id"] = cf
                    prev = prev_of.get(s["id"])
                    print(f"— Cảnh {s['id']}: ↪ frame-chain từ khung cuối nét cảnh "
                          f"{prev['id'] if prev else '?'}")
                elif not kwargs.get("image_id"):
                    print(f"— Cảnh {s['id']}: link_prev nhưng THIẾU clip cảnh trước + không ảnh riêng → bỏ qua.")
                    continue
                else:
                    print(f"— Cảnh {s['id']}: link_prev fail (thiếu clip trước) → fallback ảnh riêng.")
            mid = None
            for attempt in (1, 2):  # retry 1 lần theo chính sách lỗi
                print(f"— Cảnh {s['id']} [{mode}] lần {attempt}…")
                mid = await gen_and_fetch_clip(bridge, mode, s["prompt"],
                                               m.get("aspect", "portrait"),
                                               int(s.get("duration", 8)), str(out), **kwargs)
                if mid:
                    break
            new_clip = {"file": str(out.relative_to(pdir)), "media_id": mid,
                        "status": "done" if mid else "failed"}
            s["clip"] = new_clip
            patch_scene(pdir, s["id"], "clip", new_clip)  # merge-save: chỉ ghi field mình sở hữu
            print(f"  {'✓' if mid else '✗ FAILED (đã ghi manifest, gen lại bằng --scene ' + str(s['id']) + ')'}")
        failed = [s["id"] for s in m["scenes"] if s.get("clip", {}).get("status") == "failed"]
        print(f"Hoàn tất. Failed: {failed or 'không'}")
    finally:
        await bridge.close()


async def cmd_extract_chain(a):
    """Trích TRƯỚC khung chain/refprev để NGƯỜI DUYỆT trước khi scene-clips đốt credit
    (luật: mọi khung đầu phải qua mắt người). scene-clips thấy file đã tồn tại → dùng lại."""
    pdir = Path(a.project)
    m = load_manifest(pdir)
    prev_of = {m["scenes"][i]["id"]: (m["scenes"][i - 1] if i > 0 else None)
               for i in range(len(m["scenes"]))}
    done, miss = [], []
    for s in m["scenes"]:
        if a.scene and s["id"] not in a.scene:
            continue
        for flag, kind in (("link_prev", "chain"), ("ref_prev", "refprev")):
            if not s.get(flag):
                continue
            out = pdir / "03_images" / f"scene{s['id']:02d}_{kind}.png"
            if out.exists() and not a.force:
                done.append((s["id"], kind, out, "đã có"))
                continue
            if out.exists():
                out.unlink()
            fp = _prev_frame(pdir, prev_of.get(s["id"]), s["id"], kind)
            (done if fp else miss).append((s["id"], kind, out, "trích mới") if fp
                                          else (s["id"], kind, out, "THIẾU clip cảnh trước"))
    for sid, kind, out, note in done:
        print(f"— Cảnh {sid} [{kind}]: {out.relative_to(pdir)} ({note})")
    for sid, kind, _, note in miss:
        print(f"✗ Cảnh {sid} [{kind}]: {note} — gen clip cảnh trước rồi chạy lại.")
    if done:
        print("\nDUYỆT các khung trên (mở ảnh xem: nét? đúng bối cảnh? không AI-tell?) "
              "rồi mới scene-clips. Khung xấu → xoá file để scene-clips trích lại, "
              "hoặc tắt link_prev/ref_prev cảnh đó.")


def _subject_bits(m: dict, s: dict, cid: str) -> str:
    """Desc nhân vật + state thị giác (wardrobe/condition/held_props) — dùng chung
    compile & compose để 2 đường tả MỘT KIỂU (nguồn sự thật duy nhất)."""
    chars = {c["id"]: c for c in m.get("characters", [])}
    props = {p["id"]: p for p in m.get("props", [])}
    st = effective_state(m, s)
    if cid not in chars or not chars[cid].get("desc"):
        return ""
    bits = [chars[cid]["desc"]]
    for key in ("wardrobe", "condition"):
        v = ((st.get(key) or {}).get(cid) or "").strip()
        if v:
            bits.append(v)
    held = [props[pid]["desc"] for pid in (st.get("held_props") or {}).get(cid, [])
            if pid in props and props[pid].get("desc")]
    if held:
        bits.append("holding " + ", ".join(held))
    return ", ".join(bits)


async def cmd_compose_frame(a):
    """COMPOSITE FIRST-FRAME cho cảnh ĐÔNG thực thể (>3 ứng viên neo — vượt ngân sách ref):
    ghép DẦN từng thực thể vào 1 khung hình đầu bằng T2I/I2I nhiều lượt (MIỄN PHÍ credit).
    Mỗi lượt ≤3 ref (ảnh lượt trước + anchor thực thể mới) nhưng TÍCH LŨY → khung cuối chứa
    TẤT CẢ trong pixel, né hẳn giới hạn 3 ref của 1 generation. Duyệt khung rồi mới i2v.
    Lưu từng lượt sceneNN_comp_K.png để lần lại khi lệch; kết quả cuối ghi vào scene.image."""
    pdir = Path(a.project)
    m = load_manifest(pdir)
    s = next((x for x in m["scenes"] if x["id"] == a.scene), None)
    if not s:
        raise SystemExit(f"Không thấy cảnh {a.scene}.")
    chars = {c["id"]: c for c in m.get("characters", [])}
    props = {p["id"]: p for p in m.get("props", [])}
    st = effective_state(m, s)

    # Kế hoạch lượt: base = location + nhân vật ĐẦU (quan trọng nhất, đứng đầu list =
    # ưu tiên slot); mỗi lượt sau THÊM 1 thực thể (nhân vật kế / hero-prop chưa ai cầm).
    cids = [cid for cid in s.get("characters", []) if cid in chars]
    if not cids:
        raise SystemExit("Cảnh không có nhân vật hợp lệ — composite chỉ đáng khi đông thực thể.")
    add_props = [pid for pid in s.get("props") or []
                 if props.get(pid, {}).get("hero") and (props[pid].get("anchor") or {}).get("media_id")
                 and pid not in {h for hs in (st.get("held_props") or {}).values() for h in hs}]

    loc = next((l for l in m.get("locations", []) if l.get("id") == s.get("location")), None)
    loc_pick = _pick_anchor((loc or {}).get("anchors", []), s.get("location_angle", "")) if loc else None
    style_bits = [x for x in (m.get("style", "").strip(),
                              _TIME_EN.get((st.get("time_of_day") or "").strip(), ""),
                              (st.get("weather") or "").strip()) if x]
    rec = _recipe(s.get("emotion", "")) or {}
    shot = _SHOT.get((s.get("shot_size") or rec.get("shot_size", "")).strip(), "") or "wide shot"
    angle = _ANGLE.get((s.get("camera_angle") or rec.get("camera_angle", "")).strip(), "")

    bridge = await open_bridge()
    try:
        pid_flow = m.get("flow_project_id") or DEFAULT_PROJECT
        # ── Lượt 1 (base): bối cảnh + nhân vật đầu ──
        first = cids[0]
        base_prompt = ". ".join(x for x in (
            ", ".join(b for b in (shot, angle) if b),
            _subject_bits(m, s, first),
            (loc or {}).get("desc", ""),
            (s.get("action") or "").strip(),
            ", ".join(style_bits)) if x) + NO_TEXT
        refs = [x["media_id"] for x in (
            _pick_anchor(chars[first].get("anchors", []), s.get("angle", "front")), loc_pick) if x]
        steps = [(f"base ({first} + bối cảnh)", base_prompt, refs)]
        for k, ent in enumerate([("char", c) for c in cids[1:]] + [("prop", p) for p in add_props], 2):
            kind, eid = ent
            desc = _subject_bits(m, s, eid) if kind == "char" else props[eid]["desc"]
            anchor = _pick_anchor(chars[eid].get("anchors", []), s.get("angle", "front")) \
                if kind == "char" else props[eid].get("anchor")
            add_prompt = (f"Add {desc} into the scene, placed naturally to fit: "
                          f"{(s.get('action') or 'the scene').strip()}. Keep every existing person, "
                          f"the layout, lighting and style EXACTLY unchanged" + NO_TEXT)
            steps.append((f"thêm {eid}", add_prompt,
                          [x for x in [None, (anchor or {}).get("media_id")] if x]))  # [0] điền sau = ảnh lượt trước

        last_mid, last_file = None, None
        for i, (label, prompt, refs) in enumerate(steps, 1):
            if i > 1:
                refs = [last_mid] + refs  # ảnh lượt trước đứng ĐẦU: nền giữ nguyên, anchor mới thêm vào
            out = pdir / "03_images" / f"scene{s['id']:02d}_comp_{i}.png"
            print(f"— Lượt {i}/{len(steps)}: {label} (refs={len(refs)})")
            results = await generate_image(bridge, prompt, m.get("aspect", "portrait"),
                                           pid_flow, count=1, ref_media_ids=refs or None)
            if not results:
                raise SystemExit(f"  ✗ lượt {i} gen lỗi — các lượt trước còn trong 03_images/, chạy lại.")
            out.parent.mkdir(parents=True, exist_ok=True)
            await download_image(bridge, results[0]["image_url"], str(out))
            last_mid, last_file = results[0]["media_id"], out
        new_img = {"file": str(last_file.relative_to(pdir)), "media_id": last_mid, "approved": False}
        patch_scene(pdir, s["id"], "image", new_img)
        print(f"\nXong {len(steps)} lượt → {last_file.relative_to(pdir)} (đã ghi scene.image, approved=false)."
              f"\nDUYỆT khung: đủ {len(cids)} nhân vật + {len(add_props)} prop? mặt khớp anchor? "
              f"Lệch → xem lại từng lượt comp_K.png tìm lượt hỏng, sửa prompt/anchor rồi chạy lại.")
    finally:
        await bridge.close()


async def cmd_stitch_shots(a):  # async khớp dispatch; thân local (ffmpeg), KHÔNG cần bridge
    """Ghép lại shot clips → sceneNN.mp4 cho các cảnh shot-first (dùng sau khi regen shot lẻ;
    scene-clips đã tự stitch khi gen xong đủ shot)."""
    pdir = Path(a.project)
    m = load_manifest(pdir)
    for s in m.get("scenes", []):
        if a.scene and s["id"] not in a.scene:
            continue
        if shot_style(s) != "separate":
            continue
        out = stitch_shots(pdir, s)
        if out:
            patch_scene(pdir, s["id"], "clip", {"file": out, "media_id": "", "status": "done"})
            print(f"— Cảnh {s['id']}: ⧉ stitch {len(s['shots'])} shot → {out}")
        else:
            print(f"— Cảnh {s['id']}: chưa stitch được (shot thiếu/failed).")


async def cmd_qc_clips(a):  # async khớp dispatch; thân local (cv2), KHÔNG cần bridge
    """QC CONTINUITY trên CLIP THẬT (chốt chặn cuối trước assemble): trích frame đầu/giữa/cuối-nét
    mỗi clip → qc_clips/ + ledger.md (sổ liên tục máy-đọc-được). Claude vision đối chiếu frame với
    ANCHOR (mặt/trang phục/prop) và với CẢNH LIỀN KỀ (ánh sáng/layout/state) theo ledger → báo lệch
    per cảnh → NGƯỜI quyết regen (mandate chất lượng: credit đổi lấy đồng bộ)."""
    import cv2
    pdir = Path(a.project)
    m = load_manifest(pdir)
    qdir = pdir / "qc_clips"
    qdir.mkdir(exist_ok=True)
    chars = {c["id"]: c for c in m.get("characters", [])}
    props = {p["id"]: p for p in m.get("props", [])}
    def grab(clip: Path, stem: str) -> dict:
        cap = cv2.VideoCapture(str(clip))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        got = {}
        for name, idx in (("start", min(2, max(total - 1, 0))), ("mid", total // 2)):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok:
                p = qdir / f"{stem}_{name}.png"
                cv2.imwrite(str(p), frame)
                got[name] = p.name
        cap.release()
        endp = qdir / f"{stem}_end.png"
        if extract_sharp_end_frame(str(clip), str(endp)):
            got["end"] = endp.name
        return got

    rows, skipped = [], []
    for s in m.get("scenes", []):
        if a.scene and s["id"] not in a.scene:
            continue
        # SHOT-FIRST: trích frame TỪNG SHOT (soi được cả nội cảnh giữa các shot)
        if shot_style(s) == "separate":
            shot_rows = []
            for sh in s["shots"]:
                cf = (sh.get("clip") or {}).get("file") or \
                    f"04_clips/scene{s['id']:02d}_s{sh.get('id')}.mp4"
                clip = pdir / cf
                if clip.exists() and clip.stat().st_size > 0:
                    shot_rows.append((sh, grab(clip, f"scene{s['id']:02d}_s{sh.get('id')}")))
            if shot_rows:
                rows.append((s, {"__shots__": shot_rows}))
            else:
                skipped.append(s["id"])
            continue
        cf = s.get("clip", {}).get("file") or f"04_clips/scene{s['id']:02d}.mp4"
        clip = pdir / cf
        if not (clip.exists() and clip.stat().st_size > 0):
            skipped.append(s["id"])
            continue
        rows.append((s, grab(clip, f"scene{s['id']:02d}")))

    lines = ["# Ledger QC clip — đối chiếu frame thật với sổ liên tục", "",
             "Checklist per cảnh (Claude vision đọc frame + mục cảnh tương ứng):",
             "1. MẶT/DÁNG mỗi nhân vật khớp ảnh anchor? (trộn mặt/đổi người = regen)",
             "2. TRANG PHỤC/THỂ TRẠNG khớp state.wardrobe/condition?",
             "3. PROP đúng desc registry? (hình dạng/màu đổi = lệch)",
             "4. ÁNH SÁNG khớp time_of_day/lighting VÀ khớp cảnh liền kề cùng location?",
             "5. BỐI CẢNH: layout nhà/cây/đồ đạc khớp location anchor + cảnh liền kề?",
             "6. AI-TELL: tay/ngón, morphing, chữ tự bịa, watermark?", ""]
    prev = None
    for s, got in rows:
        st = effective_state(m, s)
        lines.append(f"## Cảnh {s['id']} — location={s.get('location') or '—'}, "
                     f"time={st.get('time_of_day') or '—'}, weather={st.get('weather') or '—'}")
        if "__shots__" in got:
            for sh, g in got["__shots__"]:
                lines.append(f"- Shot {sh.get('id')} ({sh.get('shot_size') or '?'}, "
                             f"{sh.get('duration') or '?'}s): "
                             + " · ".join(f"qc_clips/{v}" for v in g.values()))
            lines.append("- SO NỘI CẢNH: các shot trên là CÙNG một khoảnh khắc/không gian — "
                         "ánh sáng, trang phục, vị trí đồ vật phải LIỀN tuyệt đối giữa mọi shot "
                         "(so end shot k với start shot k+1); shot con phải khớp không gian MASTER (shot đầu).")
        else:
            lines.append("- Frames: " + " · ".join(f"qc_clips/{v}" for v in got.values()))
        for cid in s.get("characters") or []:
            c = chars.get(cid) or {}
            anchor_files = ", ".join(x.get("file", "") for x in c.get("anchors", []) if x.get("file"))
            extra = [((st.get(k) or {}).get(cid) or "").strip() for k in ("wardrobe", "condition")]
            lines.append(f"- {cid}: anchor [{anchor_files or 'THIẾU'}] — desc: {c.get('desc', '?')}"
                         + ("; state: " + "; ".join(x for x in extra if x) if any(extra) else ""))
            held = (st.get("held_props") or {}).get(cid) or []
            if held:
                lines.append(f"  cầm: " + "; ".join(f"{p} ({props.get(p, {}).get('desc', '?')})" for p in held))
        for pid in s.get("props") or []:
            lines.append(f"- prop {pid}: {props.get(pid, {}).get('desc', 'KHÔNG có registry')}"
                         + (f" — anchor {props[pid]['anchor'].get('file')}"
                            if props.get(pid, {}).get("anchor") else ""))
        if prev is not None and prev.get("location") and prev.get("location") == s.get("location"):
            lines.append(f"- SO VỚI cảnh {prev['id']} (cùng location): ánh sáng, layout, "
                         "trang phục phải LIỀN — mở qc_clips/scene%02d_end.png cạnh scene%02d_start.png."
                         % (prev["id"], s["id"]))
        lines.append("")
        prev = s
    (qdir / "ledger.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Trích {len(rows)} cảnh × 3 frame → {qdir.relative_to(pdir)}/ + ledger.md"
          + (f" (bỏ qua thiếu clip: {skipped})" if skipped else ""))
    print("Bước sau: Claude Read ledger.md + các frame, đối chiếu checklist, báo lệch per cảnh — "
          "NGƯỜI quyết regen (scene-clips --regen --scene N).")


async def cmd_list_models(a):
    """Hỏi THẲNG Flow danh sách video model account được cấp (getVideoModelConfig).

    Không tốn credit. Dùng để chọn videoModelKey 'quality' thật thay vì đoán.
    """
    import urllib.parse as _url

    base = "https://labs.google/fx/api/trpc/videoFx.getVideoModelConfig"
    inp_null = _url.quote('{"json":null}')
    inp_batch = _url.quote('{"0":{"json":null}}')
    candidates = [
        (base, "GET"),
        (f"{base}?input={inp_null}", "GET"),
        (f"{base}?batch=1&input={inp_batch}", "GET"),
    ]
    if a.url:                       # cho phép override URL để thăm dò thủ công
        candidates = [(a.url, a.method)]

    bridge = await open_bridge()
    try:
        chosen = None
        for url, method in candidates:
            r = await bridge.trpc_request(url, method=method)
            status = r.get("status")
            data = r.get("data")
            if status == 200 and data:
                chosen = (url, r)
                break
            print(f"… thử {method} {url[:80]} → status={status} err={r.get('error')}",
                  file=sys.stderr)
        if not chosen:
            raise SystemExit("Không lấy được model config — xem log trên. "
                             "Có thể tên procedure/format tRPC đã đổi; "
                             "dùng --url để chỉ định thủ công (bắt HAR trên Flow).")
        url, r = chosen
        print(f"# OK: {url}\n", file=sys.stderr)
        print(json.dumps(r.get("data"), ensure_ascii=False, indent=2))
    finally:
        await bridge.close()


async def cmd_scan_models(a):
    """Quét JS bundle trang Flow → liệt kê mọi videoModelKey (t2v/i2v/r2v/fl + omni).

    MIỄN PHÍ credit, không drive UI. Cần Chrome mở tab Flow (đã login).
    """
    bridge = await open_bridge()
    try:
        r = await bridge.eval_page(timeout=90)
        data = r.get("data", r)
        if data.get("error") or r.get("error"):
            raise SystemExit(f"Scan lỗi: {data.get('error') or r.get('error')}")
        print(json.dumps(data, ensure_ascii=False, indent=2))
    finally:
        await bridge.close()


# ── main ──────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("t2i", help="gen ảnh (miễn phí credit)")
    p.add_argument("--prompt", required=True)
    p.add_argument("--aspect", default="portrait",
                   help="portrait/landscape/square/4x3/3x4")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--ref", nargs="*", help="media_id ảnh tham chiếu (I2I)")
    p.add_argument("--out", default="image.png")
    p.add_argument("--project-id", default=DEFAULT_PROJECT)
    p.set_defaults(fn=cmd_t2i)

    p = sub.add_parser("upload-image", help="upload ảnh local → media_id")
    p.add_argument("path")
    p.add_argument("--project-id", default=DEFAULT_PROJECT)
    p.set_defaults(fn=cmd_upload_image)

    p = sub.add_parser("clip", help="gen 1 clip (TỐN credit)")
    p.add_argument("--mode", choices=["t2v", "i2v", "r2v", "fl", "v2v"], required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--aspect", default="portrait", help="portrait/landscape")
    p.add_argument("--duration", type=int, default=8, choices=[4, 6, 8, 10])
    p.add_argument("--image-id", help="media_id ảnh đầu (i2v/fl)")
    p.add_argument("--end-id", help="media_id ảnh cuối (fl)")
    p.add_argument("--ref", nargs="*", help="media_id ảnh tham chiếu (r2v)")
    p.add_argument("--video-id", dest="video_id", help="media_id video nguồn (v2v — sửa clip đã có)")
    p.add_argument("--video-file", dest="video_file", help="video local upload rồi sửa (v2v)")
    p.add_argument("--out", default="clip.mp4")
    p.add_argument("--no-clean", action="store_true", help="không xóa watermark")
    p.add_argument("--project-id", default=DEFAULT_PROJECT)
    p.set_defaults(fn=cmd_clip)

    p = sub.add_parser("compile-prompts", help="ghép scenes[].prompt từ field craft (local, miễn phí)")
    p.add_argument("--project", required=True, help="thư mục dự án chứa project.json")
    p.add_argument("--scene", type=int, nargs="*", help="chỉ các cảnh này")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", help="in prompt ra, KHÔNG ghi manifest")
    p.set_defaults(fn=cmd_compile_prompts)

    p = sub.add_parser("qc-storyboard",
                       help="đo luật ngữ pháp cảnh (nhịp/góc/transition/continuity) — warn-only, local")
    p.add_argument("--project", required=True, help="thư mục dự án chứa project.json")
    p.set_defaults(fn=cmd_qc_storyboard)

    p = sub.add_parser("scene-images", help="batch gen ảnh khung đầu theo project.json")
    p.add_argument("--project", required=True, help="thư mục dự án chứa project.json")
    p.add_argument("--scene", type=int, nargs="*", help="chỉ các cảnh này")
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--allow-text", dest="allow_text", action="store_true",
                   help="cho phép chữ trong ảnh (mặc định tự nối 'no text…' chống AI bịa chữ/thư pháp)")
    p.set_defaults(fn=cmd_scene_images)

    p = sub.add_parser("scene-clips", help="batch gen clip các cảnh đã duyệt ảnh (TỐN credit)")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, nargs="*", help="chỉ các cảnh này")
    p.add_argument("--regen", action="store_true", help="gen lại cả cảnh đã done")
    p.add_argument("--force", action="store_true", help="bỏ qua kiểm tra gate character_lock")
    p.set_defaults(fn=cmd_scene_clips)

    p = sub.add_parser("compose-frame",
                       help="COMPOSITE khung đầu cảnh ĐÔNG thực thể: ghép dần từng nhân vật/prop "
                            "bằng edit ảnh nhiều lượt (miễn phí) — né giới hạn 3 ref")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, required=True, help="1 cảnh mỗi lần (duyệt từng khung)")
    p.set_defaults(fn=cmd_compose_frame)

    p = sub.add_parser("extract-chain",
                       help="trích TRƯỚC khung chain/refprev từ clip cảnh trước để NGƯỜI duyệt "
                            "(scene-clips dùng lại file đã duyệt, không trích lại)")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, nargs="*", help="chỉ các cảnh này")
    p.add_argument("--force", action="store_true", help="trích lại đè file cũ")
    p.set_defaults(fn=cmd_extract_chain)

    p = sub.add_parser("stitch-shots",
                       help="ghép lại shot clips → sceneNN.mp4 (tự chạy sau scene-clips; "
                            "lệnh này cho lúc regen shot lẻ xong, local)")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, nargs="*", help="chỉ các cảnh này")
    p.set_defaults(fn=cmd_stitch_shots)

    p = sub.add_parser("qc-clips",
                       help="QC continuity trên CLIP THẬT: trích frame đầu/giữa/cuối + ledger.md "
                            "để đối chiếu anchor & cảnh liền kề trước khi assemble (local)")
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, nargs="*", help="chỉ các cảnh này")
    p.set_defaults(fn=cmd_qc_clips)

    p = sub.add_parser("list-models",
                       help="hỏi Flow danh sách video model được cấp (getVideoModelConfig, "
                            "MIỄN PHÍ) — chọn videoModelKey 'quality' thật thay vì đoán")
    p.add_argument("--url", default=None,
                   help="override URL tRPC thủ công (khi procedure đổi tên)")
    p.add_argument("--method", default="GET")
    p.set_defaults(fn=cmd_list_models)

    p = sub.add_parser("scan-models",
                       help="quét JS bundle trang Flow → liệt kê mọi videoModelKey "
                            "(t2v/i2v/r2v/fl + omni), MIỄN PHÍ, cần tab Flow đang mở")
    p.set_defaults(fn=cmd_scan_models)

    a = ap.parse_args()
    asyncio.run(a.fn(a))


if __name__ == "__main__":
    main()

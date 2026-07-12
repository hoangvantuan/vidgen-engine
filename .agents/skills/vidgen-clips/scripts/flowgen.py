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
  compile-prompts  Ghép scenes[].prompt từ field craft (hỗ trợ shots[] → timestamp coverage)
  qc-storyboard    Đo luật ngữ pháp cảnh (nhịp/góc/transition/continuity) — warn-only

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
NO_TEXT = ", no text, no letters, no words, no captions, no watermark, no signage"


def patch_scene(project_dir: Path, scene_id, key: str, value):
    """Re-load manifest từ đĩa, CHỈ set scenes[sid][key]=value rồi ghi atomic.
    Giữ đúng hợp đồng schema (script chỉ đụng field nó sở hữu) → sửa tay giữa chừng không bị đè im lặng."""
    m = load_manifest(project_dir)
    for sc in m.get("scenes", []):
        if sc.get("id") == scene_id:
            sc[key] = value
            break
    save_manifest(project_dir, m)


def _pick_anchor(anchors: list, angle: str):
    """Chọn anchor đúng angle (có media_id), fallback anchor đầu có media_id."""
    return next((a for a in anchors if a.get("angle") == angle and a.get("media_id")),
                next((a for a in anchors if a.get("media_id")), None))


def anchor_ids_for_scene(m: dict, scene: dict) -> list[str]:
    """Gom media_id anchor: NHÂN VẬT (theo angle) + BỐI CẢNH (location) — tối đa 3 ref/prompt.
    Nhân vật ưu tiên trước (giữ danh tính); location anchor thêm để khoá bối cảnh nếu còn chỗ."""
    ids = []
    chars = {c["id"]: c for c in m.get("characters", [])}
    for cid in scene.get("characters", []):
        c = chars.get(cid)
        if not c:
            continue
        pick = _pick_anchor(c.get("anchors", []), scene.get("angle", "front"))
        if pick:
            ids.append(pick["media_id"])
    lid = scene.get("location")
    if lid:
        loc = next((l for l in m.get("locations", []) if l.get("id") == lid), None)
        if loc:
            pick = _pick_anchor(loc.get("anchors", []), scene.get("location_angle", ""))
            if pick and pick["media_id"] not in ids:
                ids.append(pick["media_id"])
    return ids[:3]


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


def compile_scene_prompt(m: dict, s: dict) -> tuple[str | None, str]:
    """Ghép prompt Veo từ field craft. Trả (prompt|None, note).
    None = bỏ qua (override / thiếu liệu). Idempotent, emotion auto-fill field trống.
    Cảnh có shots[] → coverage: chuỗi timestamp thay [Cinematography]+[Action]."""
    if s.get("prompt_override"):
        return None, "giữ nguyên (prompt_override — prompt viết tay)"
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

    # [Subject] — nhắc NGUYÊN VĂN desc nhân vật + thoại trong hình
    chars = {c["id"]: c for c in m.get("characters", [])}
    subj = [chars[cid]["desc"] for cid in s.get("characters", []) if cid in chars and chars[cid].get("desc")]
    for d in s.get("dialogue", []) or []:
        line = (d.get("line") or "").strip()
        if line:
            subj.append(f'the character says "{line}"')

    # [Context] — khoá bối cảnh: lặp nguyên văn desc location
    locs = {l["id"]: l for l in m.get("locations", [])}
    context = ""
    lid = s.get("location")
    if lid and lid in locs and locs[lid].get("desc"):
        context = locs[lid]["desc"]

    # [Style & Ambiance] — style chung dự án + ánh sáng + atmosphere + keyword emotion + sfx
    amb = [m.get("style", "").strip(), _LIGHT.get(lighting, lighting), _ATMOS.get(atmosphere, atmosphere),
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
    changed, skipped, warned = [], [], []
    for s in m.get("scenes", []):
        if a.scene and s["id"] not in a.scene:
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

    # E · shots[] hợp lệ + VO khớp nhịp đọc (~3-4 chữ/giây)
    for s in scenes:
        for i, sh in enumerate(s.get("shots") or [], 1):
            f, t = sh.get("from", 0), sh.get("to", 0)
            if t <= f:
                W.append(("SHOTS", f"cảnh {s['id']} shots[{i}]: from/to không tăng ({f}→{t})."))
            elif not (1.5 <= t - f <= 4.5):
                I.append(("SHOTS", f"cảnh {s['id']} shots[{i}]: cú {t - f}s — nên 2-4s/cú."))
        last = (s.get("shots") or [{}])[-1].get("to")
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
    todo = [s for s in m["scenes"]
            if (not a.scene or s["id"] in a.scene)
            and s.get("mode", "i2v") in ("i2v", "fl")
            and not (s.get("image", {}).get("media_id") and s["image"].get("approved"))]
    if not todo:
        print("Không có cảnh nào cần gen ảnh (đã đủ hoặc đã duyệt hết).")
        return
    bridge = await open_bridge()
    try:
        for s in todo:
            refs = anchor_ids_for_scene(m, s)
            out = pdir / "03_images" / f"scene{s['id']:02d}.png"
            print(f"— Cảnh {s['id']}: gen ảnh (refs={len(refs)})")
            prompt = s["prompt"] + ("" if a.allow_text else NO_TEXT)
            results = await generate_image(bridge, prompt, m.get("aspect", "portrait"),
                                           m.get("flow_project_id") or DEFAULT_PROJECT,
                                           count=a.count, ref_media_ids=refs or None)
            if not results:
                print(f"  ✗ cảnh {s['id']} gen ảnh lỗi — bỏ qua, chạy lại sau.")
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            await download_image(bridge, results[0]["image_url"], str(out))
            new_img = {"file": str(out.relative_to(pdir)),
                       "media_id": results[0]["media_id"], "approved": False}
            s["image"] = new_img
            patch_scene(pdir, s["id"], "image", new_img)  # merge-save: không đè sửa tay giữa chừng
        print("Xong. Duyệt ảnh trong 03_images/ rồi set image.approved=true trước khi scene-clips.")
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
            mode = s.get("mode", "i2v")
            out = pdir / "04_clips" / f"scene{s['id']:02d}.mp4"
            kwargs = dict(project_id=m.get("flow_project_id") or DEFAULT_PROJECT)
            if mode in ("i2v", "fl"):
                kwargs["image_id"] = s.get("image", {}).get("media_id")
            if mode == "fl":
                kwargs["end_id"] = s.get("end_image", {}).get("media_id")
            if mode == "r2v":
                kwargs["ref_ids"] = anchor_ids_for_scene(m, s)
            # ── FRAME-CHAINING: khung cuối NÉT của cảnh trước → khung đầu cảnh này ──
            if s.get("link_prev") and mode in ("i2v", "fl"):
                prev = prev_of.get(s["id"])
                prev_clip = None
                if prev:
                    pf = prev.get("clip", {}).get("file") or f"04_clips/scene{prev['id']:02d}.mp4"
                    cand = pdir / pf
                    if cand.exists() and cand.stat().st_size > 0:
                        prev_clip = cand
                cf = None
                if prev_clip:
                    frame_png = pdir / "03_images" / f"scene{s['id']:02d}_chain.png"
                    if extract_sharp_end_frame(str(prev_clip), str(frame_png)):
                        cf = await upload_image(bridge, str(frame_png), kwargs["project_id"])
                if cf:
                    kwargs["image_id"] = cf
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

    a = ap.parse_args()
    asyncio.run(a.fn(a))


if __name__ == "__main__":
    main()

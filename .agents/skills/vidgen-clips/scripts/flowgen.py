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

Chạy bằng python có deps (websockets, cv2, numpy): ~/.venv/claude/bin/python
Ví dụ:
  PY=~/.venv/claude/bin/python
  $PY flowgen.py t2i --prompt "..." --aspect portrait --out anchor.png
  $PY flowgen.py scene-images --project projects/con-cao
  $PY flowgen.py scene-clips  --project projects/con-cao
"""
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


def anchor_ids_for_scene(m: dict, scene: dict) -> list[str]:
    """Gom media_id anchor của các nhân vật trong cảnh (tối đa 3 ref/prompt)."""
    ids = []
    chars = {c["id"]: c for c in m.get("characters", [])}
    for cid in scene.get("characters", []):
        c = chars.get(cid)
        if not c:
            continue
        angle = scene.get("angle", "front")
        anchors = c.get("anchors", [])
        pick = next((a for a in anchors if a.get("angle") == angle and a.get("media_id")),
                    next((a for a in anchors if a.get("media_id")), None))
        if pick:
            ids.append(pick["media_id"])
    return ids[:3]


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
    todo = []
    for s in m["scenes"]:
        if a.scene and s["id"] not in a.scene:
            continue
        if s.get("clip", {}).get("status") == "done" and not a.regen:
            continue
        mode = s.get("mode", "i2v")
        if mode in ("i2v", "fl") and not s.get("image", {}).get("approved"):
            print(f"— Cảnh {s['id']}: ảnh chưa duyệt, bỏ qua.")
            continue
        todo.append(s)
    if not todo:
        print("Không có cảnh nào cần gen clip.")
        return
    print(f"Sẽ gen {len(todo)} clip (TỐN credit). Resume: cảnh done sẽ không gen lại.")
    bridge = await open_bridge()
    try:
        for s in todo:
            mode = s.get("mode", "i2v")
            out = pdir / "04_clips" / f"scene{s['id']:02d}.mp4"
            kwargs = dict(project_id=m.get("flow_project_id") or DEFAULT_PROJECT)
            if mode in ("i2v", "fl"):
                kwargs["image_id"] = s["image"]["media_id"]
            if mode == "fl":
                kwargs["end_id"] = s.get("end_image", {}).get("media_id")
            if mode == "r2v":
                kwargs["ref_ids"] = anchor_ids_for_scene(m, s)
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

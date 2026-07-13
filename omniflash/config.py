"""Flow Agent — Configuration.

All constants hardcoded. No external config files needed.
"""

import os

# ─── Paths ───────────────────────────────────────────────────

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_ID_FILE = os.path.join(ROOT_DIR, "media-id.js")

# ─── Project ─────────────────────────────────────────────────

DEFAULT_PROJECT = "0143adf4-5864-4cb4-abb5-fe4254ad0dc7"

# Image model (imageModelName gửi lên Flow batchGenerateImages). Lựa chọn:
#   GEM_PIX_2 = Nano Banana 2 (Gempix2)  ·  IMAGEN_4 = Imagen 4  ·  NARWHAL = Imagen (đời cũ)
IMAGE_MODEL = "GEM_PIX_2"

# ─── Hardcoded constants (never change) ──────────────────────

API_KEY = "AIzaSyBtrm0o5ab1c-Ec8ZuLcGt3oJAA5VWt3pY"
API_BASE = "https://aisandbox-pa.googleapis.com"

CLIENT_CTX = {
    "tool": "PINHOLE",
    # Tier account — xác thực từ HAR Flow UI (2026-07): tài khoản trả phí là TIER_TWO.
    # Gửi sai tier → Flow có thể chặn/hạ cấp model. Override qua env FLOW_PAYGATE_TIER.
    "tier": os.environ.get("FLOW_PAYGATE_TIER", "PAYGATE_TIER_TWO"),
    "origin": "https://labs.google",
    "recaptcha_app_type": "RECAPTCHA_APPLICATION_TYPE_WEB",
}

# ─── Video model keys (videoModelKey) ────────────────────────
# CHỐT theo request GEN THẬT của Flow UI (HAR + capture qua extension, 2026-07-13,
# verify bằng gen clip thật qua pipeline). Naming KHÔNG đồng nhất giữa các mode:
#
#   · t2v  = "veo_3_1_t2v"        — Veo 3.1, KHÔNG duration trong key, ra ~8s CỐ ĐỊNH.
#                                    ✅ verify: gen clip thật (192f/24 = 8s).
#   · i2v  = "abra_i2v_<dur>s"    — codename abra, DURATION trong key, ra ĐÚNG duration.
#                                    ✅ verify: gen clip thật (dur=4 → 96f/24 = 4s).
#                                    (veo_3_1_i2v KHÔNG tồn tại → HTTP 500 "Internal error".)
#   · fl   = "abra_fl_<dur>s"     — ⚠️ suy luận theo pattern abra_<mode>_<dur>s, CHƯA verify.
#   · r2v  = "abra_r2v_<dur>s"    — ⚠️ suy luận, CHƯA verify (Flow phân biệt referenceImages
#                                    vs 'ingredients'(Omni) — xem log). Verify khi chạy thật.
#
# Ghi chú tier: dropdown Flow có modelFamilyId veo_3_1_quality/fast/lite (React fiber);
#   đó là lựa chọn UI, request cơ bản KHÔNG kèm field tier. Muốn ÉP Quality cần bắt thêm HAR.
# Override từng mode qua env FLOW_VMK_<MODE> (vd FLOW_VMK_I2V=abra_i2v_6s). Nhánh legacy:
#   FLOW_VIDEO_MODEL=abra ⇒ mọi mode dùng abra_<mode>_<dur>s.
VIDEO_MODEL = os.environ.get("FLOW_VIDEO_MODEL", "auto")


def video_model_key(mode: str, duration: int = 0) -> str:
    """Trả videoModelKey THẬT cho mode gen (verify từ request Flow UI 2026-07-13).

    Override per-mode qua env FLOW_VMK_<MODE>. FLOW_VIDEO_MODEL=abra ⇒ toàn abra_<mode>.
    """
    env = os.environ.get(f"FLOW_VMK_{mode.upper()}")
    if env:
        return env
    if VIDEO_MODEL == "abra":
        return f"abra_{mode}_{duration}s"
    if mode == "t2v":
        return "veo_3_1_t2v"                      # Veo 3.1 (tốt nhất, verify)
    return f"abra_{mode}_{duration}s"             # i2v verify; fl/r2v suy luận

ASPECTS = {
    "portrait": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "landscape": "VIDEO_ASPECT_RATIO_LANDSCAPE",
}

ENDPOINTS = {
    "generate_t2v": "/v1/video:batchAsyncGenerateVideoText",
    "generate_i2v": "/v1/video:batchAsyncGenerateVideoStartImage",
    "generate_fl": "/v1/video:batchAsyncGenerateVideoStartAndEndImage",
    "generate_r2v": "/v1/video:batchAsyncGenerateVideoReferenceImages",
    "generate_edit": "/v1/video:batchAsyncGenerateVideoEditVideo",
    "upload_image": "/v1/flow/uploadImage",
    "poll_status": "/v1/video:batchCheckAsyncVideoGenerationStatus",
    "get_media": "/v1/media/{media_id}",
    "get_credits": "/v1/credits",
}

MODELS = {
    "t2v": {
        4: "abra_t2v_4s",
        6: "abra_t2v_6s",
        8: "abra_t2v_8s",
        10: "abra_t2v_10s",
    },
    "edit": "abra_edit",
}

DURATIONS = [4, 6, 8, 10]
DEFAULT_DURATION = 10
MAX_COUNT = 4

CREDITS_PER_VIDEO = {
    4: 5,
    6: 10,
    8: 10,
    10: 15,
}

# ─── Runtime constants ───────────────────────────────────────

WS_PORT = int(os.environ.get("WS_PORT", "9222"))
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8100"))

POLL_INTERVAL = 10
POLL_TIMEOUT = 420

SEGMENT_DURATION = 10
FPS = 24

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
]

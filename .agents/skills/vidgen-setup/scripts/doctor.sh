#!/bin/bash
# doctor.sh — khám sức khỏe môi trường vidgen/flow-agent. Chạy: bash doctor.sh
# Không sửa gì cả, chỉ chẩn đoán + in cách khắc phục từng mục.
PY="$HOME/.venv/claude/bin/python"
PASS=0; WARN=0; FAIL=0
ok()   { echo "✅ $1"; PASS=$((PASS+1)); }
warn() { echo "⚠️  $1"; echo "   ↳ $2"; WARN=$((WARN+1)); }
bad()  { echo "❌ $1"; echo "   ↳ $2"; FAIL=$((FAIL+1)); }

echo "═══ vidgen doctor ═══"

# 1. Python venv + deps
if [ -x "$PY" ]; then
  MISSING=$("$PY" - <<'EOF'
mods = {"websockets": "websockets", "cv2": "opencv-python-headless", "numpy": "numpy", "elevenlabs": "elevenlabs"}
missing = []
for m, pkg in mods.items():
    try: __import__(m)
    except ImportError: missing.append(pkg)
print(" ".join(missing))
EOF
)
  if [ -z "$MISSING" ]; then ok "Python venv + deps (websockets, cv2, numpy, elevenlabs)"
  else bad "Thiếu package: $MISSING" "uv pip install --python ~/.venv/claude/bin/python $MISSING"; fi
else
  bad "Chưa có venv ~/.venv/claude" "uv venv ~/.venv/claude && uv pip install --python ~/.venv/claude/bin/python websockets opencv-python-headless numpy elevenlabs"
fi

# 2. ffmpeg + các filter pipeline cần
if command -v ffmpeg >/dev/null; then
  FILTERS=$(ffmpeg -hide_banner -filters 2>/dev/null)
  MISS=""
  for f in subtitles xfade zoompan sidechaincompress amix; do
    echo "$FILTERS" | grep -q " $f " || MISS="$MISS $f"
  done
  if [ -z "$MISS" ]; then ok "ffmpeg đủ filter (subtitles/xfade/zoompan/sidechaincompress/amix)"
  else bad "ffmpeg thiếu filter:$MISS" "Bản brew rút gọn — cài bản đủ libass: brew reinstall ffmpeg (kiểm: ffmpeg -version | grep enable-libass). Thiếu subtitles vẫn chạy được: assemble tự xuất sub rời."; fi
else
  bad "Chưa có ffmpeg" "brew install ffmpeg"
fi

# 3. Engine bundle (omniflash + extension nằm ngay trong repo — không cần clone gì thêm)
ENGINE_ROOT="$(cd "$(dirname "$0")/../../../.." 2>/dev/null && pwd)"
if [ -d "$ENGINE_ROOT/omniflash" ] && [ -f "$ENGINE_ROOT/extension/manifest.json" ]; then
  ok "Engine bundle đủ (omniflash/ + extension/ tại $ENGINE_ROOT)"
else
  bad "Thiếu omniflash/ hoặc extension/ ở root repo" "Repo không toàn vẹn — git checkout lại, hoặc override tạm bằng env FLOW_AGENT_ROOT / vidgen.config.json trỏ tới repo flow-agent ngoài"
fi

# 4. Chrome + extension (chỉ kiểm tĩnh được — extension connected phải nhìn badge)
if [ -d "/Applications/Google Chrome.app" ]; then ok "Google Chrome đã cài"
else bad "Không thấy Google Chrome" "Cài Chrome rồi load extension/ của repo này (chrome://extensions → Developer mode → Load unpacked)"; fi

# 5. Port bridge 9222/8100 (bận = script cũ còn chạy → batch mới sẽ lỗi)
BUSY=""
for p in 9222 8100; do lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 && BUSY="$BUSY $p"; done
if [ -z "$BUSY" ]; then ok "Port 9222/8100 rảnh (bridge sẵn sàng)"
else warn "Port$BUSY đang bận" "Script flow-agent khác đang chạy. Nhớ: bridge=8100, FastAPI=8000 — đừng nhầm. Kill nếu là tiến trình treo: lsof -nP -iTCP:9222 -sTCP:LISTEN"; fi

# 6. ELEVENLABS_API_KEY — phân biệt 3 trạng thái gần-giống: chưa-set / set-chưa-export / export-OK.
#    NHÂN thật: doctor chạy bằng `bash`, KHÔNG tự load ~/.zshenv (của zsh) → phải hỏi qua zsh,
#    nếu không sẽ false-negative "chưa set" trong khi shell thật (zsh) có biến.
KEY_VAL=""; KEY_ENV=""
if command -v zsh >/dev/null 2>&1; then
  KEY_VAL=$(zsh -c 'source ~/.zshenv 2>/dev/null; source ~/.zshrc 2>/dev/null; print -rn -- $ELEVENLABS_API_KEY' 2>/dev/null)
  KEY_ENV=$(zsh -c 'source ~/.zshenv 2>/dev/null; source ~/.zshrc 2>/dev/null; printenv ELEVENLABS_API_KEY' 2>/dev/null)
fi
[ -z "$KEY_VAL" ] && KEY_VAL="$ELEVENLABS_API_KEY"
[ -z "$KEY_ENV" ] && env | grep -q '^ELEVENLABS_API_KEY=' && KEY_ENV="$ELEVENLABS_API_KEY"
if [ -n "$KEY_ENV" ]; then
  TIER=$(curl -s -m 8 -H "xi-api-key: $KEY_ENV" https://api.elevenlabs.io/v1/user/subscription 2>/dev/null | grep -o '"tier":"[^"]*"' | cut -d'"' -f4)
  case "$TIER" in
    "")     warn "ELEVENLABS_API_KEY đã export nhưng không kiểm được tier" "Mạng/proxy? Thử: curl -H \"xi-api-key: \$ELEVENLABS_API_KEY\" https://api.elevenlabs.io/v1/user/subscription" ;;
    "free") warn "ElevenLabs tier FREE" "Free hay bị chặn TTS (401 detected_unusual_activity) — cần gói trả phí để làm giọng đọc ổn định" ;;
    *)      ok "ELEVENLABS_API_KEY đã export, hợp lệ (tier: $TIER)" ;;
  esac
elif [ -n "$KEY_VAL" ]; then
  warn "ELEVENLABS_API_KEY có trong shell nhưng CHƯA export" "Python (tiến trình con) sẽ KeyError dù shell thấy. Sửa GỐC: đổi dòng trong ~/.zshenv thành 'export ELEVENLABS_API_KEY=...'. Tạm thời: chạy 'export ELEVENLABS_API_KEY' đầu mỗi lệnh."
else
  warn "Chưa set ELEVENLABS_API_KEY" "Chỉ cần khi video có lời đọc. Set trong ~/.zshenv (nhớ 'export') hoặc dùng skill setup-api-key."
fi

# 7. Font tiếng Việt cho sub (bundle trong vidgen-assemble)
FONT_DIR="$(cd "$(dirname "$0")/../../vidgen-assemble/assets/fonts" 2>/dev/null && pwd)"
if [ -n "$FONT_DIR" ] && ls "$FONT_DIR"/BeVietnamPro-*.ttf >/dev/null 2>&1; then
  ok "Font Be Vietnam Pro (đủ dấu tiếng Việt): $FONT_DIR"
else
  warn "Không thấy font Be Vietnam Pro bundle" "Sub có thể mất dấu. Tải Be Vietnam Pro rồi trỏ assemble.py --fonts-dir <thư mục font>"
fi

echo "─────────────────────"
echo "Kết quả: $PASS ✅ · $WARN ⚠️ · $FAIL ❌"
[ $FAIL -eq 0 ] && echo "Sẵn sàng chạy vidgen-flow. (Extension connected kiểm lúc chạy thật: badge XANH trên icon extension.)"
exit $FAIL

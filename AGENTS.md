# Harness: vidgen-engine — sản xuất video AI từ ý tưởng tới final.mp4

**Mục tiêu:** biến ý tưởng thành video hoàn chỉnh (kịch bản → nhân vật nhất quán → gen clip
bằng flow-agent → ráp giọng + phụ đề + nhạc) với 3 cổng duyệt của con người.

**Trigger:** yêu cầu làm/sản xuất video, tiếp tục dự án video, gen lại cảnh → dùng skill
`vidgen-flow` (orchestrator, tự gọi 5 skill còn lại). Máy mới / lỗi môi trường → `vidgen-setup`.
Chỉnh video có sẵn (cắt, transcribe, color) → skill `video-use` (ngoài harness này).

**Quy ước:**
- Dự án video: `projects/<tên>/` + manifest `project.json`
  (schema: `.agents/skills/vidgen-script/references/project-schema.md`).
- Script chạy bằng `~/.venv/claude/bin/python` (websockets, opencv, numpy, elevenlabs).
- Engine gen **bundle sẵn trong repo**: `omniflash/` + `extension/` + `cli/` (nguồn từ
  kodelyx/flow-agent) — không phụ thuộc repo ngoài. Override khi cần engine khác:
  env `FLOW_AGENT_ROOT` hoặc `vidgen.config.json` (rỗng = dùng bundle).
- Skill nằm ở `.agents/skills/`, symlink `.claude/skills → ../.agents/skills`
  để Claude Code nhận. Script tự tìm root theo độ sâu này (flowgen.py `parents[4]`,
  doctor.sh `../../../..`) — move skill là phải sửa cả hai.

**Biến đổi lịch sử:**
| Ngày | Thay đổi | Đối tượng | Lý do |
|------|----------|-----------|-------|
| 2026-07-03 | Khởi tạo harness vidgen: 5 skill (flow/script/character/clips/assemble) | .agents/skills/vidgen-* | Xây bộ skill làm video generic dùng flow-agent, tách khỏi akasto-* |
| 2026-07-03 | Thêm bảng tư vấn loại video phù hợp ở Bước 1 | vidgen-script, vidgen-flow | User yêu cầu skill gợi ý loại video thay vì bắt user tự chọn |
| 2026-07-03 | Hấp thụ bài học SOP bẫy #11-14: retime max(1.0), fallback Ken Burns, -an + scale 720→1080, phát hiện thiếu libass, Veo chặn ngầm, port 8100/8000 | vidgen-assemble, vidgen-clips | Bài học thật từ flow-agent/docs/SOP-clip-real-tu-anh-tinh-akasto.md |
| 2026-07-03 | v2: transition per-cut theo cảm xúc (xfade, bù overlap); thêm skill vidgen-setup + doctor.sh | vidgen-assemble, vidgen-script, vidgen-setup | ffmpeg đã có libass; cần khám môi trường trước khi chạy |
| 2026-07-03 | Move toàn bộ harness từ flow-agent sang PERSONAL/vidgen-engine, standalone hóa (vidgen.config.json, bundle font) | toàn bộ | User muốn tách engine thành project riêng |
| 2026-07-03 | Move bộ skill từ `.agents/skills/` ra `skills/` (root), cập nhật mọi đường dẫn tham chiếu | AGENTS.md, README.md, skills/*/SKILL.md | Chuẩn hóa layout: skill nằm ở root repo |
| 2026-07-03 | Move skill về lại `.agents/skills/` + symlink `.claude/skills`; sửa độ sâu tìm root (flowgen.py parents[4], doctor.sh 4 cấp) | .agents/skills, .claude/skills, flowgen.py, doctor.sh | Claude Code đọc skill qua .claude/skills; layout skills/ root bỏ |
| 2026-07-03 | Vendor engine flow-agent vào repo: omniflash/ + extension/ + cli/ + requirements.txt + docs/flow-agent/; vidgen.config.json thành override tùy chọn; bỏ omni.py, test_api.py, media-id.js (không gì trong repo dùng) | omniflash, extension, cli, docs, README, doctor.sh, vidgen-setup | Hết phụ thuộc repo ngoài — clone 1 repo là chạy được |

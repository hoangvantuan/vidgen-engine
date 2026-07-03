---
name: vidgen-flow
description: ORCHESTRATOR sản xuất video AI từ Ý TƯỞNG tới FILE .MP4 CUỐI bằng flow-agent (Google Flow, không API key) — kịch bản → nhân vật nhất quán → gen clip hàng loạt → ráp giọng+sub+nhạc. Dùng khi user muốn "làm video", "tạo video từ ý tưởng", "sản xuất video AI", "làm video kể chuyện", "làm short/reel", "video 9:16/16:9", và các yêu cầu TIẾP TỤC: "chạy tiếp dự án video", "gen lại cảnh N", "đổi giọng đọc", "sửa kịch bản rồi làm tiếp", "ráp lại". NGOẠI LỆ: video cho brand Akasto → akasto-video-flow; chỉnh sửa video CÓ SẴN (cắt, transcribe, color) → video-use.
---

# Vidgen Flow (orchestrator: ý tưởng → video production)

**Thực thi:** main session tự lái, KHÔNG agent team. Đi tuần tự 4 stage, dừng ở 3 GATE
chờ user duyệt. Song song thật sự (batch gen) nằm trong script Python của stage 3.

**Triết lý gate — đặt cổng ở chỗ sửa sai ĐẮT nhất:** chữ rẻ → ảnh miễn phí → video tốn
credit → ráp tốn công. Chốt từng lớp trước khi trả tiền cho lớp sau.

```
Ý tưởng ─▶ STEP 1 vidgen-script ──🚦GATE 1 script lock
                 ─▶ STEP 2 vidgen-character (anchor + clip thử) ──🚦GATE 2 character lock
                 ─▶ STEP 3 vidgen-clips (batch, tự chạy) 
                 ─▶ STEP 4 vidgen-assemble ──🚦GATE 3 final review ─▶ 06_final/final.mp4
```

## STEP 0 · Nhận diện ngữ cảnh (luôn làm trước tiên)

1. User có nhắc dự án cũ hoặc `projects/<tên>/project.json` tồn tại?
   - **Có + yêu cầu sửa một phần** ("gen lại cảnh 5", "đổi giọng") → đọc manifest, nhảy
     thẳng tới stage liên quan, KHÔNG chạy lại từ đầu.
   - **Có + ý tưởng mới** → tạo dự án mới, đặt tên khác.
   - **Không** → dự án mới: tạo `projects/<slug>/` + tạo TodoWrite 1 todo/STEP.
2. Đọc trạng thái `gates` trong manifest — gate nào đã mở thì không hỏi lại.
3. Kiểm nhanh môi trường khi sắp tới stage cần: Chrome + extension (stage 3),
   `ELEVENLABS_API_KEY` (stage 4 có lời đọc), `ffmpeg` (stage 4).

## STEP 1 · Kịch bản — skill `vidgen-script`

Tư vấn LOẠI video phù hợp trước (bảng gợi ý trong vidgen-script) → **thiết kế hook mở đầu** →
brief 5 câu → kịch bản → `project.json` (schema + references craft trong vidgen-script/).
**🚦 GATE 1:** trình kịch bản + storyboard (kiểm hook 3s/30s, cấu trúc kể, đa dạng cỡ cảnh, 1 CTA).
User gật → `gates.script_lock=true`.
Chưa gật → KHÔNG đụng tới gen. Video không nhân vật cố định (phong cảnh, b-roll) →
sau gate 1 bỏ qua STEP 2, mở luôn `character_lock` và ghi chú lý do.

## STEP 2 · Nhân vật — skill `vidgen-character`

Char sheet (người duyệt) → anchors (máy bám) → **1 clip thử** (đốt credit nhỏ trước khi đốt lớn).
**🚦 GATE 2:** trình sheet + anchors + clip thử (kiểm khớp anchor, không AI-tell). User gật → `gates.character_lock=true`.

## STEP 3 · Gen clip — skill `vidgen-clips` (tự chạy, không gate)

`scene-images` (miễn phí) → user duyệt ảnh theo lô → **báo số clip sẽ gen ≈ số credit** →
`scene-clips` (resume theo manifest, retry 1, failed không chặn batch). QC nhanh từng clip.
Đây là điểm tiết kiệm nhất: mọi chỉnh sửa hình ảnh làm ở tầng ẢNH, đừng ở tầng VIDEO.

## STEP 4 · Ráp — skill `vidgen-assemble`

TTS + **phụ đề karaoke** + timings → assemble (setpts khớp lời, auto-pick nhạc theo mood, ducking, end-card).
**🚦 GATE 3:** trình final.mp4 + tự-QC (sub karaoke khớp, nhạc không đè giọng, hook mạnh, không cụt).
User gật → `gates.final_approved=true` → bàn giao.

## Xử lý lỗi (chung mọi stage)

- Mỗi thao tác lỗi: retry 1 lần → vẫn hỏng thì ghi nhận (manifest/báo cáo), đi tiếp phần khác,
  cuối stage tổng hợp danh sách hỏng cho user quyết.
- **Không bao giờ** tự chi thêm credit ngoài kế hoạch đã báo (gen lại hàng loạt phải hỏi).
- Sai từ gốc (kịch bản hỏng khi đã gen nửa chừng) → DỪNG, quay về stage gốc, báo rõ
  chi phí đã mất + sẽ mất, chờ user quyết.

## Test scenario

**Luồng chuẩn:** "làm video kể chuyện con cáo và chùm nho, 9:16, ~1 phút" → STEP 0 tạo
`projects/con-cao-va-chum-nho/` → STEP 1 brief+kịch bản 6-8 cảnh 🚦 → STEP 2 anchor cáo
+ clip thử 🚦 → STEP 3 gen 6-8 ảnh → duyệt → 6-8 clip → STEP 4 TTS+ráp 🚦 → final.mp4.

**Luồng lỗi:** STEP 3 cảnh 4 gen failed 2 lần (prompt bị chặn) → manifest ghi `failed`,
batch chạy tiếp cảnh 5-8 → cuối stage báo: "cảnh 4 hỏng vì X, đề xuất sửa prompt thành Y" →
user gật → `--scene 4 --regen` → đủ clip → sang STEP 4.

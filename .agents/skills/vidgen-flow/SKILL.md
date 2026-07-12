---
name: vidgen-flow
description: ORCHESTRATOR sản xuất video AI từ Ý TƯỞNG tới FILE .MP4 CUỐI bằng flow-agent (Google Flow, không API key) — kịch bản → nhân vật nhất quán → gen clip hàng loạt → ráp giọng+sub+nhạc. Dùng khi user muốn "làm video", "tạo video từ ý tưởng", "sản xuất video AI", "làm video kể chuyện", "làm short/reel", "video 9:16/16:9", và các yêu cầu TIẾP TỤC: "chạy tiếp dự án video", "gen lại cảnh N", "đổi giọng đọc", "sửa kịch bản rồi làm tiếp", "ráp lại". NGOẠI LỆ: video cho brand Akasto → akasto-video-flow; chỉnh sửa video CÓ SẴN (cắt, transcribe, color) → video-use.
---

# Vidgen Flow (orchestrator: ý tưởng → video production)

**Thực thi:** main session tự lái, KHÔNG agent team. Đi tuần tự 4 stage, dừng ở **4 GATE**
chờ user duyệt (stage 1 có 2 gate: kịch bản rồi storyboard). Song song thật sự (batch gen)
nằm trong script Python của stage 3.

**Triết lý gate — đặt cổng ở chỗ sửa sai ĐẮT nhất:** chữ rẻ → ảnh miễn phí → video tốn
credit → ráp tốn công. Chốt từng lớp trước khi trả tiền cho lớp sau.

**Gate là điểm PHẢN BIỆN, không phải xin chữ ký** (chi tiết:
`../vidgen-script/references/decision-grilling.md`): trước khi trình user ở mỗi gate, tự soi
output ở góc *tìm lỗi* (đảo ngược: "cái này SAI kiểu gì mà mình đang bỏ qua?"), rồi **nêu
1-2 rủi ro còn lại + hỏi thẳng**, đừng mở lời bằng "ổn rồi, duyệt nhé". Mọi quyết định hỏi
user (loại video, giọng đọc…) đều theo cùng lối grilling: **từng câu một, kèm đề xuất, tự
suy chỗ đã rõ**.

```
Ý tưởng ─▶ STEP 1 vidgen-script ──🚦GATE 1A story lock (kịch bản) ──🚦GATE 1B script lock (storyboard)
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

## STEP 1 · Kịch bản — skill `vidgen-script` (2 GATE, LUÔN tách)

Tư vấn LOẠI video phù hợp trước (bảng gợi ý trong vidgen-script) → **thiết kế hook mở đầu** →
brief 5 câu → viết kịch bản (lời VO) → **🚦 GATE 1A** → dựng storyboard → **🚦 GATE 1B**. Mọi video
đều tách 2 gate, kể cả reel ngắn — kịch bản duyệt riêng trước, đắt sửa sau.

**🚦 GATE 1A · story lock** (kịch bản — CHẶN dựng storyboard): trình bản **lời VO đọc-to** (chưa kèm
prompt). Phản biện **cả mạch truyện** không chỉ hook — through-line (`turn`+`payoff` cùng trục?),
open loop (cấy-đóng?), mạch (cảnh thừa/gãy?), lời (đọc-to vấp không?). User gật → `gates.story_lock=true`.
**Chưa gật → KHÔNG dựng storyboard** (không compile prompt).

**🚦 GATE 1B · script lock** (storyboard/prompt): sau khi compile — chạy `flowgen qc-storyboard`
(máy đo nhịp/góc/transition/continuity, warn-only) rồi trình field/prompt KÈM kết quả QC: mỗi ⚠
hoặc đã sửa hoặc nêu lý do phá cách (kiểm cỡ cảnh + góc máy đa dạng, nhịp duration biến thiên,
beat đắt có coverage `shots[]`, continuity, không "THIẾU LIỆU", 1 CTA). User gật → `gates.script_lock=true`.
Chưa gật → KHÔNG đụng tới gen. Video không nhân vật cố định (phong cảnh, b-roll) →
sau GATE 1B bỏ qua STEP 2, mở luôn `character_lock` và ghi chú lý do.
Backward-compat: dự án cũ thiếu `story_lock` → coi như đã mở, chạy y nguyên.

## STEP 2 · Nhân vật — skill `vidgen-character`

Char sheet (người duyệt) → anchors (máy bám) → **1 clip thử** (đốt credit nhỏ trước khi đốt lớn).
Clip thử là **phép thăm dò năng lực engine ở tầng video** — chọn cảnh **RỦI RO CAO NHẤT** (nội dung nhạy
cảm nhất, tương tác phức tạp nhất), KHÔNG phải cảnh trung bình: ranh giới ảnh→video có safety filter khác
nhau, ảnh gen được ≠ clip gen được (xem `vidgen-character` Bước 3).
**🚦 GATE 2:** trình sheet + anchors + clip thử (kiểm khớp anchor, không AI-tell). User gật → `gates.character_lock=true`.

## STEP 3 · Gen clip — skill `vidgen-clips` (tự chạy + vòng QC continuity)

`scene-images` / `compose-frame` (cảnh `composite:true`, miễn phí) → user duyệt KHUNG ĐẦU theo lô
(LUẬT: mọi khung, kể cả khung chain `extract-chain`, qua mắt người trước khi đốt credit) → **báo số
clip sẽ gen ≈ số credit** → `scene-clips` (resume theo manifest, retry 1, failed không chặn batch).
Đây là điểm tiết kiệm nhất: mọi chỉnh sửa hình ảnh làm ở tầng ẢNH, đừng ở tầng VIDEO.
**Sau batch — vòng `qc-clips` (chốt chặn cuối trước ráp):** máy trích frame + ledger → Claude
vision đối chiếu anchor/state/cảnh liền kề → báo danh sách lệch → user quyết regen → regen xong
qc-clips LẠI cảnh đó. Chỉ sang STEP 4 khi danh sách lệch = rỗng hoặc user chấp nhận phần còn lại.
Clip fail `MEDIA_GENERATION_STATUS_FAILED` = Veo chặn nội dung (hay gặp: trẻ em + đau khổ) → **mềm prompt**
(bỏ `gaunt/frail/starving`, diễn khổ qua bối cảnh/trang phục) rồi gen lại; vẫn chặn → fallback Ken Burns từ
ảnh (assemble tự làm). Bảng từ-trigger: `vidgen-clips/references/veo-prompt-craft.md`.

## STEP 4 · Ráp — skill `vidgen-assemble`

TTS + **phụ đề karaoke** + timings → (tùy chọn `gen_sfx.py` gen SFX cảnh chủ chốt) → assemble (setpts khớp
lời, auto-pick nhạc theo mood, ducking dịu, mix SFX layer, end-card). Muốn hiệu ứng âm thanh (gió, bước chân,
trẻ cười) thì gen SFX vì assemble bỏ audio gốc Veo.
**🚦 GATE 3:** trình final.mp4 + tự-QC (sub karaoke khớp, nhạc/ SFX không đè giọng, hook mạnh, không cụt).
User gật → (tùy chọn) **áp bộ nhận diện thương hiệu** nếu dự án có brand preset:
`apply_brand.py --project projects/<tên> --brand <tên>` → `06_final/final_overlay.mp4` (intro
logo→watermark + end-card hero nở + CTA url). Cần preset `assets/brands/<tên>/` (xem `assets/brands/README.md`).
Chi tiết: `vidgen-assemble` Bước 2b. → `gates.final_approved=true` → bàn giao bản cuối
(`final_overlay.mp4` nếu áp brand, không thì `final.mp4`).

## Xử lý lỗi (chung mọi stage)

- Mỗi thao tác lỗi: retry 1 lần → vẫn hỏng thì ghi nhận (manifest/báo cáo), đi tiếp phần khác,
  cuối stage tổng hợp danh sách hỏng cho user quyết.
- **Không bao giờ** tự chi thêm credit ngoài kế hoạch đã báo (gen lại hàng loạt phải hỏi).
- Sai từ gốc (kịch bản hỏng khi đã gen nửa chừng) → DỪNG, quay về stage gốc, báo rõ
  chi phí đã mất + sẽ mất, chờ user quyết.

## Test scenario

**Luồng chuẩn:** "làm video kể chuyện con cáo và chùm nho, 9:16, ~1 phút" → STEP 0 tạo
`projects/con-cao-va-chum-nho/` → STEP 1 brief+kịch bản 6-8 cảnh 🚦(1A lời)🚦(1B storyboard) → STEP 2 anchor cáo
+ clip thử 🚦 → STEP 3 gen 6-8 ảnh → duyệt → 6-8 clip → STEP 4 TTS+ráp 🚦 → final.mp4.

**Luồng lỗi:** STEP 3 cảnh 4 gen failed 2 lần (prompt bị chặn) → manifest ghi `failed`,
batch chạy tiếp cảnh 5-8 → cuối stage báo: "cảnh 4 hỏng vì X, đề xuất sửa prompt thành Y" →
user gật → `--scene 4 --regen` → đủ clip → sang STEP 4.

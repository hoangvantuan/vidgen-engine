# Giữ nhân vật nhất quán & tránh AI-tell (Stage 2 · vidgen-character)

Bằng chứng chính thức Google (verify 3-0). Điểm cốt lõi đã được research **xác nhận đúng hướng đi
hiện tại của skill** (dùng ảnh-anchor), và **bác bỏ** một lối phổ biến (chỉ tả chi tiết bằng chữ).

## 1 · Đường ĐÚNG: ảnh-anchor (reference image), KHÔNG phải seed, KHÔNG phải chỉ mô tả

- **BÁC BỎ (verify 0-3):** "giữ nhân vật nhất quán bằng mô tả chi tiết ngoại hình/giọng/hành động
  trong prompt, càng chi tiết càng nhất quán" — nghe chính thức nhưng **không đứng vững**.
- **XÁC NHẬN (verify 3-0):** giữ nhất quán bằng **ẢNH THAM CHIẾU** (tính năng "Ingredients to
  Video" của Veo 3.1):
  1. **Tạo ảnh anchor** nhân vật/bối cảnh/style trước (Google dùng Gemini 2.5 Flash Image; ở đây
     ta dùng T2I của flow-agent — MIỄN PHÍ credit, gen tới khi ưng).
  2. **Đưa ảnh anchor vào Veo** làm reference để giữ thẩm mỹ nhất quán qua nhiều shot.
- **KHÔNG dùng seed** cho việc này — nhất quán đến từ ảnh, không từ seed số.

→ Đúng kiến trúc skill hiện tại: **char sheet cho NGƯỜI duyệt danh tính · anchor cho MÁY bám theo**.
Nạp nhầm char sheet (nhiều góc/đám đông) vào Flow → AI trộn mặt. Anchor phải: **1 người/ảnh · 1
góc · nền trơn · rõ mặt · style đồng bộ giữa mọi anchor**.

## 2 · Chuẩn ảnh anchor (từ nguồn craft)

- **Chính diện (front-facing), ánh sáng trung tính**, nền sạch.
- Nếu cần ổn định hình học khuôn mặt → thêm **nhiều góc** (nghiêng/side, 3/4). Mỗi góc = 1 anchor
  riêng, ghi `angle` đúng (flowgen chọn anchor khớp `angle` của cảnh).
- Gen TỪNG anchor riêng, **không cắt từ char sheet** (chất lượng thấp).
- **Đồng bộ ngược `desc`:** anchor sinh chi tiết ngoài `desc` mà muốn giữ → cập nhật
  `characters[].desc` cho khớp anchor (desc là nguồn sự thật đưa vào prompt mọi cảnh; lệch = cảnh sau mâu thuẫn).

## 3 · Mô tả bằng chữ vẫn hữu ích — nhưng là HỖ TRỢ, không thay ảnh

- Ảnh anchor là chính. **Nhắc lại `characters[].desc` nguyên văn trong prompt mỗi cảnh** vẫn nên
  làm (hỗ trợ ảnh, giữ chi tiết trang phục/màu) — chỉ đừng KỲ VỌNG chữ thay được ảnh.

## 3b · Đồng bộ TOÀN DIỆN — mọi thực thể lặp lại phải có nguồn sự thật + anchor

Nguyên lý (grill 2026-07-12 "nhân vật đồng bộ nhưng chi tiết khác lệch"): hệ chỉ neo được cái
CÓ HỢP ĐỒNG. Nhân vật chính có desc+anchor thì giữ được; nhân vật phụ/prop/ánh sáng là chữ tự do
→ trôi. Bảng cách khoá theo loại thực thể:

| Thực thể | Cách khoá | Ghi chú |
|---|---|---|
| Nhân vật (chính + PHỤ) | entry `characters[]` + anchor riêng 1-người/ảnh | mặt-rõ hoặc ≥2 cảnh = bắt buộc; đám đông → né mặt trong action |
| Prop lặp ≥2 cảnh | `props[]` registry (desc chuẩn); hero-prop thêm ảnh anchor | prop gắn bối cảnh → BAKE vào ảnh location anchor |
| Bối cảnh | location anchor ĐỦ 9 GÓC từ Grid 3×3 | góc thiếu anchor = Veo bịa layout |
| Ánh sáng/thời điểm | `state.time_of_day/weather` + QC đo trôi | không khoá bằng ảnh |
| Trạng thái nhân vật | `state.wardrobe/condition/held_props` | sổ liên tục — compiler chèn phần THỊ GIÁC |

**Cảnh ĐÔNG thực thể (>3 ứng viên neo) — composite first-frame** (`flowgen compose-frame`):
ghép DẦN từng thực thể vào 1 khung hình đầu qua nhiều lượt edit ảnh miễn phí (mỗi lượt ≤3 ref,
tích lũy), duyệt khung, rồi i2v. Khung chứa tất cả trong pixel → né hẳn giới hạn 3 ref (nguồn:
Vertex AI ghi ref workflow vốn cho 3 ảnh/MỘT chủ thể; cộng đồng hội tụ về composite-frame cho cảnh
đông — CHƯA kiểm chứng thật trên engine này, clip thử dự án đầu PHẢI kèm 1 cảnh composite).
KHÔNG mâu thuẫn luật "1 người/ảnh": luật đó áp cho ảnh làm REFERENCE danh tính (Veo không biết ai
là ai → trộn mặt); composite làm FIRST FRAME là khung hình thật của cảnh, vai khác.

**2 luật an toàn khi dùng ảnh/frame cảnh trước (link_prev / ref_prev):**
1. **Chống trôi photocopy (generation loss):** cảnh N ref frame N-1, N+1 ref N… vài đời là mặt trôi
   khỏi anchor gốc. Danh tính nhân vật LUÔN lấy từ anchor GỐC; frame cảnh trước chỉ mang vai
   không gian/ánh sáng (ref_prev THAY location anchor, không thay character anchor).
2. **Chống lây lỗi:** AI-tell của cảnh trước truyền sang cảnh sau — chỉ chain/ref từ clip đã qua
   `flowgen qc-clips`.

## 4 · Image-first workflow (duyệt frame trước khi đốt credit video)

Bằng chứng (verify 3-0): quy trình **"First and Last Frame"** — duyệt ảnh khung ĐẦU (và khung
CUỐI nếu mode `fl`) TRƯỚC khi gen; Veo tạo transition mượt (kèm audio) giữa hai ảnh.
- Kinh tế: **ảnh T2I miễn phí, video tốn credit** → luôn duyệt ảnh khung đầu (rẻ) rồi mới I2V (đắt).
- Mode `fl` (first+last): cấp cả ảnh đầu + ảnh cuối để kiểm soát điểm đầu/cuối chuyển động.

## 5 · Tránh AI-tell (thừa ngón, méo mặt, morphing)

- Negative CỤ THỂ mới ăn (không dùng "bad quality"): "stable facial features", "consistent
  proportions", "natural hands, five fingers", "steady motion".
- Giảm hành động tay phức tạp/nhanh trong 1 cảnh (nguồn hay lỗi ngón). Cảnh close-up mặt → nhấn
  "consistent face matching reference".
- Soi clip thử ở gate 2: mặt có khớp anchor? có morphing giữa các frame? tay/ngón có bất thường?

## Map vào stage

- **Tạo nhân vật (Stage 2):** dựng char sheet + anchor theo chuẩn mục 1-2; ghi `media_id` vào
  `characters[].anchors[]`.
- **Gen clip (Stage 3):** image-first — flowgen tự lấy anchor đúng `angle` làm ref cho ảnh khung đầu.
- Checklist gate 2: anchor 1-người/1-góc/nền trơn? clip thử giữ mặt khớp anchor? không AI-tell?

## Nguồn (verify 3-0, nguồn chính thức)

- blog.google/innovation-and-ai/technology/ai/veo-3-1-ingredients-to-video
- cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1
  (Ingredients to Video, First and Last Frame)
- ĐÃ BÁC (không dựa vào): "mô tả chữ chi tiết = nhất quán" (deepmind prompt-guide, verify 0-3).

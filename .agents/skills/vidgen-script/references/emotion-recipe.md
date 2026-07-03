# Emotion → Recipe — bảng auto-fill cho prompt compiler

**Mục đích:** biến MỘT ý đồ cảm xúc (`scenes[].emotion`) thành công thức hình ảnh nhất quán —
góc máy + cỡ cảnh + ánh sáng + khí quyển. Compiler dùng bảng này để **auto-fill** khi các field
`camera_angle` / `lighting` / `atmosphere` / `shot_size` để trống. **Điền tay luôn thắng** auto-fill.

**Nguồn:** khung "Emotion Mapping — Master Class: Kết Hợp Mọi Yếu Tố Để Kể Chuyện Bằng Tiềm Thức"
(CinematicHubClone / AI Cinematic Framework). 6 công thức kinh điển dưới đây **giữ nguyên** từ nguồn;
cột "keyword EN" là thuật ngữ điện ảnh chuẩn để nhét vào prompt Veo (tiếng Anh).

> Cách dùng gốc theo nguồn: "lấy các keyword rồi nối bằng dấu phẩy để AI ra đúng Mood bạn cần".
> Compiler tự động hoá đúng thao tác đó.

---

## Bảng 6 công thức cảm xúc

### 1. `fear` / `tension` — Sợ hãi, bất an
Thế giới đè bẹp nhân vật, mất phương hướng, nguy hiểm rình rập.
- **camera_angle:** Dutch Angle · Low Angle · POV → `dutch` (mặc định) / `low`
- **shot_size:** close / extreme_close (dồn ép)
- **lighting:** Low-key · Chiaroscuro → `low_key`
- **atmosphere:** Fog · Smoke · Storm → `fog`
- **keyword EN:** `dutch angle, low-key lighting, chiaroscuro, fog, ominous shadows, unsettling`
- Ví dụ: trốn trong tủ khi kẻ lạ tới; khám phá nhà hoang trong sương; giây trước thảm họa.

### 2. `joy` — Vui vẻ, lạc quan
An toàn, ấm áp, cởi mở, tràn sức sống. Khán giả thư giãn hoàn toàn.
- **camera_angle:** Eye Level · High Angle nhẹ → `eye_level`
- **shot_size:** wide / medium / full
- **lighting:** High-key · Golden Hour → `high_key`
- **atmosphere:** Clear Sky · Sunny → `` (trời trong, không cần hiệu ứng)
- **keyword EN:** `eye level, high-key lighting, golden hour, clear sunny sky, warm, vibrant, airy`
- Ví dụ: gia đình đoàn tụ trên biển; quảng cáo lifestyle/du lịch; nhận tin vui.

### 3. `sadness` / `loneliness` — Buồn bã, cô đơn
Thu mình, trống rỗng, cô lập nhân vật khỏi thế giới.
- **camera_angle:** High Angle · Overhead → `high`
- **shot_size:** extreme_wide / wide (để thấy sự nhỏ bé) → `wide`
- **lighting:** Blue Hour · Low-key → `blue_hour`
- **atmosphere:** `` (không gian trống, tùy chọn haze nhẹ)
- **keyword EN:** `high angle, overhead shot, extreme wide shot, blue hour, low-key, isolated, empty space, melancholic`
- Ví dụ: gặm nhấm nỗi đau trong phòng tối; ngồi một mình giữa thành phố vô hồn.

### 4. `power` / `dominance` — Quyền lực, áp đảo
Phóng đại tầm vóc nhân vật, bắt khán giả ngước nhìn.
- **camera_angle:** Low Angle · Worm's Eye → `low`
- **shot_size:** cowboy / full / medium_close_up → `medium`
- **lighting:** Rembrandt · Rim Light → `rembrandt`
- **atmosphere:** God Rays · Smoke mỏng → `god_rays`
- **keyword EN:** `low angle, worm's eye view, rembrandt lighting, rim light, god rays, thin smoke, imposing`
- Ví dụ: bài phát biểu của hoàng đế; sếp tổng bước vào phòng họp.

### 5. `romance` / `intimacy` — Lãng mạn, thân mật
Xóa mờ khoảng cách, tập trung vào kết nối hai thực thể. Ấm áp, riêng tư.
- **camera_angle:** eye_level (ngang tầm, thân mật) → `eye_level`
- **shot_size:** close / medium_close_up (nối kết) → `close`
- **lighting:** Golden Hour · Rim Light mềm → `golden_hour`
- **atmosphere:** Rain nhẹ · Warm Glow → `` (warm glow nhúng qua lighting)
- **keyword EN:** `eye level, close-up, golden hour, soft rim light, warm glow, gentle rain, intimate, shallow depth of field`
- Ví dụ: hẹn hò đầu tiên, nụ hôn; ánh mắt giao nhau chốn đông người; đám cưới hoàng hôn.

### 6. `chaos` / `madness` — Hỗn loạn, điên loạn
Phá vỡ trật tự thị giác, không có đường chân trời vững, ánh sáng chớp giật.
- **camera_angle:** Dutch Angle · Handheld → `dutch`
- **shot_size:** medium / close-up sát → `close`
- **lighting:** Low-key · Strobe (đèn chớp) → `low_key`
- **atmosphere:** Dust · Storm · Neon loạn → `dust`
- **keyword EN:** `dutch angle, handheld, low-key, strobe flashes, dust, chaotic neon, disorienting, no stable horizon`
- Ví dụ: tâm trí bẻ gãy hóa điên; khởi đầu đại chiến; mắc kẹt trong bạo động.

---

## Biến thể suy ra (KHÔNG có trong nguồn — dùng khi cần, đánh dấu rõ)

Các cảm xúc dưới không nằm trong 6 công thức gốc; đây là mặc định **suy luận từ quy ước điện ảnh**,
dùng tạm khi kịch bản cần — coi là điểm khởi đầu, nên tinh chỉnh tay:
- `calm` — eye_level · medium/wide · soft/high_key · atmosphere trống. `soft natural light, balanced, serene`.
- `wonder` — low/eye_level · wide/establishing · god_rays hoặc golden_hour. `awe, sweeping, luminous, god rays`.

---

## Quy tắc compiler áp bảng này (khớp `flowgen compile-prompts`)

1. Chỉ auto-fill field **để trống**; field điền tay giữ nguyên.
2. Thứ tự ưu tiên khi ghép `[Cinematography]`: field tay > recipe theo `emotion` > mặc định trung tính.
3. `emotion` trống + field craft trống → compiler dùng mô tả trung tính, KHÔNG bịa cảm xúc.
4. **Đa dạng cỡ cảnh:** dù emotion gợi ý shot_size, compiler KHÔNG ép mọi cảnh cùng cỡ — nếu 2 cảnh
   liền kề cùng emotion, luân phiên trong nhóm cỡ cảnh gợi ý (chống nhịp thị giác đơn điệu).
5. Keyword EN nối bằng dấu phẩy, đặt vào đúng khối prompt (angle/lighting → [Cinematography] &
   [Style & Ambiance]; atmosphere → [Style & Ambiance]).

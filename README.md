<div align="center">

# 🎬 Vidgen Engine

**Sản xuất video AI từ ý tưởng tới `final.mp4` — không cần API key gen hình.**

Bộ 6 skill cho Claude Code + engine gen bundle sẵn trong repo, kết nối Google Flow/Veo qua
Chrome extension. ElevenLabs làm giọng đọc, ffmpeg ráp dựng, Remotion overlay title/end-card.

</div>

```
Ý tưởng ─▶ Kịch bản + Storyboard ──🚦──▶ Nhân vật + bối cảnh ──🚦──▶ Gen clip hàng loạt ─▶ Ráp ──🚦──▶ final.mp4
            (vidgen-script)              (vidgen-character)          (vidgen-clips)        (vidgen-assemble)
                                     3 cổng duyệt của con người, đặt ở chỗ sửa sai ĐẮT nhất
```

Điều khiển bằng lời qua Claude Code — không cần nhớ lệnh. Nói *"làm video kể chuyện con cáo
và chùm nho, 9:16, 1 phút"* và skill `vidgen-flow` đi hết 4 stage, dừng đúng ở 3 gate cần
người duyệt.

---

## Vì sao dùng

- **Miễn phí phần tốn nhất** — hình gen qua tài khoản Google Flow thật (không API key). Ảnh (T2I) hoàn toàn miễn phí; chỉ clip (I2V) mới đốt credit Flow.
- **Sửa rẻ nhờ tầng hoá** — kịch bản, nhân vật, clip, giọng, ráp là 5 tầng độc lập. Đổi lời kể không phải gen lại clip; hỏng 1 cảnh chỉ gen lại cảnh đó.
- **Không mất tiến độ** — `project.json` ghi trạng thái từng cảnh (atomic) sau mỗi bước. Đứt giữa chừng chạy lại không gen trùng, không mất gì.
- **Nhất quán nhân vật + bối cảnh** — anchor nhân vật, location anchor (Grid Method 3×3) và frame-chaining giữ cùng một khuôn mặt, một không gian, một tỉ lệ xuyên suốt.
- **Chạy được ngay** — engine gen (`omniflash/` + `extension/`) bundle sẵn trong repo, clone 1 lần là chạy, không phụ thuộc repo ngoài.

## Triết lý thiết kế

1. **Image-first, credit-last** — mọi chỉnh sửa hình ảnh làm ở tầng ẢNH (miễn phí), chỉ animate khi đã duyệt.
2. **Manifest là nguồn sự thật** — `project.json` là trung tâm. Prompt Veo là field **dẫn xuất** (compile lại được từ các field cảnh), không gõ tay từng cái.
3. **Gate ở chỗ đắt** — script lock (chữ rẻ) → character lock + clip thử (đốt nhỏ trước đốt lớn) → final review. Giữa các gate máy tự chạy.
4. **Sửa tại ranh giới, không vá triệu chứng** — lỗi pipeline sinh ở ranh giới giữa 2 tầng (schema↔engine, producer↔consumer). Fix = hợp đồng tường minh + kiểm fail-fast tại nguồn.

## Bộ skill

| Skill | Vai trò |
|---|---|
| **vidgen-flow** | Orchestrator: nhận ý tưởng, đi 4 stage, dừng ở 3 gate, resume dự án cũ |
| **vidgen-script** | Tư vấn loại video phù hợp → brief → kịch bản → storyboard `project.json` |
| **vidgen-character** | Char sheet (người duyệt) → anchor nhân vật + **location anchor** (Grid Method 3×3, khoá bối cảnh + tỉ lệ) → clip thử → character lock |
| **vidgen-clips** | `flowgen.py`: **`compile-prompts`** (field cảnh → prompt Veo 5 khối) · T2I/I2V/T2V/R2V/FL/**V2V** batch qua omniflash · **frame-chaining** `link_prev` · poll + tải + xoá watermark + resume |
| **vidgen-assemble** | `tts_to_ass.py` (**phụ đề karaoke word-level**) · `gen_sfx.py` + `assemble.py` (retime khớp lời, xfade theo cảm xúc, **auto-pick nhạc theo mood** + ducking, **lớp SFX** dưới giọng, Ken Burns fallback, **Remotion overlay** opt-in) |
| **vidgen-setup** | `doctor.sh` khám môi trường (hỏi key qua zsh) + hướng dẫn cài từng thứ |

## Yêu cầu

- **Chrome** + tài khoản Google có quyền dùng [Flow](https://labs.google/fx/tools/flow)
- **ffmpeg** có `libass` (để render phụ đề) — `doctor.sh` kiểm hộ
- **uv** (quản gói Python) và **Node.js** (chỉ khi dùng Remotion overlay)
- **ElevenLabs API key** — *chỉ cần khi video có lời đọc* (tier trả phí; free hay bị chặn TTS)

## Bắt đầu

Engine gen đã nằm sẵn trong repo — không cần clone gì thêm.

```bash
# 1. Tạo venv + cài deps Python
test -d ~/.venv/claude || uv venv ~/.venv/claude
uv pip install --python ~/.venv/claude/bin/python websockets opencv-python-headless numpy elevenlabs

# 2. Khám môi trường (báo thiếu gì, hướng dẫn cài từng thứ)
bash .agents/skills/vidgen-setup/scripts/doctor.sh
```

Nạp Chrome extension (làm tay 1 lần):

1. Chrome → `chrome://extensions` → bật **Developer mode**
2. **Load unpacked** → chọn thư mục `extension/` của **repo này**
3. Mở [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow), đăng nhập Google
4. Icon extension hiện badge **XANH** = đã kết nối

> [!TIP]
> Muốn dùng bản flow-agent ngoài (ví dụ để lấy engine mới hơn) thay bản bundle: set env
> `FLOW_AGENT_ROOT` hoặc ghi `vidgen.config.json` `{"flow_agent_root": "/duong/dan/flow-agent"}`.
> Để rỗng là dùng bản bundle trong repo.

## Dùng thế nào

Mở Claude Code trong thư mục này rồi nói bằng lời — `vidgen-flow` tự nhận diện dự án mới/cũ
và đi đúng stage:

```
"Làm video kể chuyện con cáo và chùm nho, 9:16, khoảng 1 phút"
"Gen lại cảnh 5"            "Đổi giọng đọc rồi ráp lại"
"Chạy tiếp dự án con-cao"   "Sửa kịch bản cảnh 3 rồi làm tiếp"
```

Hoặc chạy tay từng script khi cần kiểm soát chi tiết:

```bash
PY=~/.venv/claude/bin/python
CLIPS=.agents/skills/vidgen-clips/scripts/flowgen.py
ASM=.agents/skills/vidgen-assemble/scripts

$PY $CLIPS t2i --prompt "..." --out anh.png              # ảnh, miễn phí
$PY $CLIPS compile-prompts --project projects/x          # field cảnh → prompt Veo (idempotent)
$PY $CLIPS scene-images    --project projects/x          # ảnh khung đầu các cảnh
$PY $CLIPS scene-clips     --project projects/x          # clip (tốn credit) + frame-chaining

$PY $ASM/tts_to_ass.py --project projects/x --voice VOICE_ID   # phụ đề karaoke word-level
$PY $ASM/gen_sfx.py    --project projects/x                    # gen SFX từ field sfx[]
$PY $ASM/assemble.py   --project projects/x --sfx auto         # ráp: nhạc theo mood + lớp SFX
```

## Loại video hỗ trợ

Lõi generic storyboard-driven (N cảnh × clip 4–10s) + 2 preset: **kể chuyện dài** (2–6')
và **reel/short** (20–60s, hook 3 giây). Kèm theo:

- Tỉ lệ **9:16 / 16:9** · có / không lời đọc
- 4 mode gen từng cảnh: **i2v** (mặc định), t2v, r2v, fl
- 5 **style archetype** khoá tỉ lệ vật-với-vật: `true_to_life` / `heroic` / `monumental` / `storybook` / `hero_product`
- Transition per-cut theo cảm xúc: dissolve / fadewhite / fade / cut
- **Frame-chaining** (`link_prev`) nối cảnh liền mạch · fallback **Ken Burns** cho cảnh Flow từ chối gen

## Cấu trúc repo

```
vidgen-engine/
├── .agents/skills/    # 6 skill vidgen-* (flow/script/character/clips/assemble/setup)
│   └── vidgen-*/references/  # craft đã lọc qua research đối kháng: hook-and-structure,
│                             # veo-prompt-craft, emotion-recipe, consistency-and-ai-tells,
│                             # caption-and-audio, decision-grilling, project-schema
├── .claude/skills     # symlink → ../.agents/skills (để Claude Code nhận skill)
├── omniflash/         # engine gen (Python) — bundle từ flow-agent, nói chuyện với extension
├── extension/         # Chrome extension Flow Agent — load unpacked vào Chrome
├── cli/               # CLI + API server gốc của flow-agent (python -m cli.generate / cli.api / cli.sniff)
├── requirements.txt   # deps engine (websockets, opencv, numpy)
├── vidgen.config.json # override trỏ flow-agent ngoài (rỗng = dùng bundle)
├── assets/bgm/        # thư viện nhạc nền theo mood (tự thả nhạc royalty-free — xem README trong đó)
└── projects/          # các dự án video (tự tạo khi chạy, không commit)
```

Mỗi dự án video có layout riêng — trạng thái mọi cảnh nằm trong `project.json`:

```
projects/<tên>/
├── project.json      # manifest — nguồn sự thật (schema: vidgen-script/references/project-schema.md)
├── 01_script/        # brief.md + kichban.md
├── 02_characters/    # char sheet + anchor nhân vật + location anchor
├── 03_images/        # ảnh khung đầu từng cảnh (duyệt trước khi animate)
├── 04_clips/         # clip từng cảnh (đã xoá watermark)
├── 05_audio/         # narration.mp3 + subs.ass + timings.json + sfx/
└── 06_final/         # final.mp4
```

## Cách hoạt động

1. **Script** — phỏng vấn brief theo thứ tự phụ thuộc, sinh kịch bản + storyboard, điền field từng cảnh (action, emotion, camera, lighting…) vào `project.json`.
2. **Character** — người duyệt char sheet; máy gen anchor nhân vật + location anchor để Veo bám. Gen 1 clip thử ở cảnh **rủi ro nhất** (ảnh gen được ≠ clip gen được) trước khi lock.
3. **Clips** — `compile-prompts` biến field cảnh thành prompt Veo, rồi `scene-images` → `scene-clips` batch qua omniflash. Cảnh `link_prev` trích khung cuối nét nhất clip trước làm khung đầu.
4. **Assemble** — TTS ElevenLabs khớp timestamp → phụ đề karaoke → retime clip theo lời đọc → nhạc nền ducking + lớp SFX → end-card → `final.mp4`.

> [!NOTE]
> AI QC được **hình** nhưng **không nghe audio, không xem chuyển động**. Vì vậy gate cuối
> bắt buộc người duyệt xem-nghe bản dựng thật trước khi coi là xong.

## Kiến thức đã hấp thụ (trả giá thật mới có)

- Veo **chặn ngầm** một số nội dung (người trong suốt/ma, trẻ em + cảnh khổ) — retry ≤2–3 lần rồi fallback Ken Burns.
- Clip Flow ra **720×1280 + audio gốc** — luôn scale cover + `-an` khi ráp.
- Retime khớp lời: dài hơn → **cắt** giữ tốc độ thật; ngắn hơn → **slow** bằng setpts. Không freeze.
- xfade **ăn overlap** → mỗi cảnh render dư đúng phần bị ăn để video khớp narration.
- ffmpeg brew có bản **thiếu libass** — doctor kiểm trước, assemble tự xuống cấp xuất sub rời.
- Bridge callback = port **8100**, FastAPI = **8000** — đừng đoán port, đọc `/openapi.json`.
- Field schema phải có **consumer** hoặc đánh dấu **metadata-only** — `sfx[]` từng mồ côi, nay có `gen_sfx.py` (producer) + `apply_sfx_layer` (consumer).

## Giới hạn

- Cần Chrome + extension Flow Agent connected (badge xanh) — engine chạy qua tài khoản Google thật.
- Video tốn credit Flow của tài khoản; ảnh thì không.
- Gate cuối bắt buộc người duyệt (AI không nghe/không xem chuyển động).

---

Bộ skill `vidgen-*` phát hành theo giấy phép **MIT**. Phần engine bundle `omniflash/`,
`extension/`, `cli/` lấy từ [kodelyx/flow-agent](https://github.com/kodelyx/flow-agent)
(repo gốc chưa khai báo license).

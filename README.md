# 🎬 Vidgen Engine

**Sản xuất video AI từ ý tưởng tới file .mp4 cuối** — bộ 6 skill cho Claude Code,
engine gen **bundle sẵn trong repo** (`omniflash/` + `extension/`, nguồn từ
[flow-agent](https://github.com/kodelyx/flow-agent)) kết nối Google Flow/Veo qua Chrome
extension — không cần API key, không phụ thuộc repo ngoài. ElevenLabs làm giọng đọc,
ffmpeg ráp dựng.

```
Ý tưởng ─▶ Kịch bản + Storyboard ──🚦──▶ Nhân vật nhất quán ──🚦──▶ Gen clip hàng loạt ─▶ Ráp ──🚦──▶ final.mp4
           (vidgen-script)              (vidgen-character)         (vidgen-clips)        (vidgen-assemble)
                                    3 cổng duyệt của con người đặt ở chỗ sửa sai ĐẮT nhất
```

## Triết lý thiết kế

1. **Image-first, credit-last** — ảnh (T2I) miễn phí, video (I2V) tốn credit.
   Mọi chỉnh sửa hình ảnh làm ở tầng ẢNH, chỉ animate khi đã duyệt.
2. **Tầng hóa để sửa rẻ** — kịch bản, nhân vật, clip, giọng, ráp là 5 tầng độc lập.
   Đổi lời kể không phải gen lại clip; clip hỏng 1 cảnh chỉ gen lại cảnh đó.
3. **Manifest là nguồn sự thật** — `project.json` ghi trạng thái từng cảnh sau mỗi bước
   (atomic). Đứt giữa chừng chạy lại không mất gì, không gen trùng.
4. **Gate ở chỗ đắt** — script lock (chữ rẻ) → character lock + clip thử (đốt nhỏ trước
   đốt lớn) → final review. Giữa các gate máy tự chạy.

## Bộ skill

| Skill | Vai trò |
|---|---|
| **vidgen-flow** | Orchestrator: nhận ý tưởng, đi 4 stage, dừng ở 3 gate, resume dự án cũ |
| **vidgen-script** | Tư vấn loại video phù hợp → brief → kịch bản → storyboard `project.json` |
| **vidgen-character** | Char sheet (người duyệt) → anchor (máy bám) → clip thử → character lock |
| **vidgen-clips** | `flowgen.py`: T2I/I2V/T2V/R2V/FL/**V2V** batch qua omniflash, poll + tải + xóa watermark + resume (v2v = sửa clip khỏi gen lại) |
| **vidgen-assemble** | `tts_to_ass.py` (TTS timestamp → **phụ đề karaoke word-level** + timings) + `assemble.py` (retime khớp lời, xfade theo cảm xúc, **auto-pick nhạc theo mood** + ducking chuẩn, Ken Burns fallback) |
| **vidgen-setup** | `doctor.sh` khám môi trường + hướng dẫn cài từng thứ |

## Cài đặt

Engine gen (omniflash + Chrome extension) đã nằm sẵn trong repo — không cần clone gì thêm:

```bash
# 1. Yêu cầu: Chrome + tài khoản Google có Flow, ffmpeg (đủ libass), uv
test -d ~/.venv/claude || uv venv ~/.venv/claude
uv pip install --python ~/.venv/claude/bin/python websockets opencv-python-headless numpy elevenlabs

# 2. Load extension bundle vào Chrome (làm tay 1 lần)
# Chrome → chrome://extensions → Developer mode → Load unpacked → chọn thư mục extension/ của repo NÀY
# Mở labs.google/fx/tools/flow, đăng nhập Google → icon extension hiện badge XANH = connected

# 3. Khám môi trường
bash .agents/skills/vidgen-setup/scripts/doctor.sh
```

Muốn dùng bản flow-agent ngoài thay bản bundle (ví dụ để lấy engine mới hơn): set env
`FLOW_AGENT_ROOT` hoặc ghi `vidgen.config.json` `{"flow_agent_root": "/duong/dan/flow-agent"}`
— để rỗng là dùng bản bundle trong repo.

`ELEVENLABS_API_KEY` chỉ cần khi video có lời đọc (tier trả phí — free hay bị chặn TTS).

## Dùng thế nào

Mở Claude Code trong thư mục này rồi nói bằng lời:

```
"Làm video kể chuyện con cáo và chùm nho, 9:16, khoảng 1 phút"
"Gen lại cảnh 5"           "Đổi giọng đọc rồi ráp lại"
"Chạy tiếp dự án con-cao"  "Sửa kịch bản cảnh 3 rồi làm tiếp"
```

Skill `vidgen-flow` tự nhận diện dự án mới/cũ và đi đúng stage. Hoặc chạy tay từng script:

```bash
PY=~/.venv/claude/bin/python
$PY .agents/skills/vidgen-clips/scripts/flowgen.py t2i --prompt "..." --out anh.png     # ảnh, miễn phí
$PY .agents/skills/vidgen-clips/scripts/flowgen.py scene-images --project projects/x    # ảnh các cảnh
$PY .agents/skills/vidgen-clips/scripts/flowgen.py scene-clips  --project projects/x    # clip (tốn credit)
$PY .agents/skills/vidgen-assemble/scripts/tts_to_ass.py --project projects/x --voice VOICE_ID  # sub karaoke
$PY .agents/skills/vidgen-assemble/scripts/assemble.py  --project projects/x   # nhạc tự chọn theo music.mood
```

## Cấu trúc repo

```
vidgen-engine/
├── .agents/skills/    # 6 skill vidgen-* (flow/script/character/clips/assemble/setup) + references/ craft
├── .claude/skills     # symlink → ../.agents/skills (để Claude Code nhận skill)
├── omniflash/         # engine gen (Python) — bundle từ flow-agent, nói chuyện với extension
├── extension/         # Chrome extension Flow Agent — load unpacked vào Chrome
├── cli/               # CLI + API server gốc của flow-agent (python -m cli.generate / cli.api / cli.sniff)
├── requirements.txt   # deps engine (websockets, opencv, numpy)
├── vidgen.config.json # override trỏ flow-agent ngoài (rỗng = dùng bundle)
├── assets/bgm/        # thư viện nhạc nền theo mood (tự thả nhạc royalty-free — xem README trong đó)
└── projects/          # các dự án video (tự tạo khi chạy, không commit — xem .gitignore)
```

## Cấu trúc dự án video

```
projects/<tên>/
├── project.json      # manifest — nguồn sự thật (schema: vidgen-script/references/project-schema.md)
├── 01_script/        # brief.md + kichban.md
├── 02_characters/    # char sheet + anchors
├── 03_images/        # ảnh khung đầu từng cảnh (duyệt trước khi animate)
├── 04_clips/         # clip từng cảnh (đã xóa watermark)
├── 05_audio/         # narration.mp3 + subs.ass + timings.json
└── 06_final/         # final.mp4
```

## Loại video hỗ trợ

Lõi generic storyboard-driven (N cảnh × clip 4-10s) + 2 preset: **kể chuyện dài** (2-6')
và **reel/short** (20-60s, hook 3 giây). Tỉ lệ 9:16 / 16:9 · có/không lời đọc · 4 mode gen
từng cảnh (i2v mặc định, t2v, r2v, fl) · transition per-cut theo cảm xúc (dissolve/fadewhite/fade/cut)
· fallback Ken Burns cho cảnh Flow từ chối gen.

## Kiến thức đã hấp thụ (trả giá thật mới có)

- Veo **chặn ngầm** một số nội dung start-frame (người trong suốt/ma) — retry ≤2-3 lần rồi fallback.
- Clip Flow ra **720×1280 + audio gốc** — luôn scale cover + `-an` khi ráp.
- Retime khớp lời: dài hơn → **cắt** giữ tốc độ thật; ngắn hơn → **slow** bằng setpts. Không freeze.
- xfade **ăn overlap** → mỗi cảnh render dư đúng phần bị ăn để video khớp narration.
- ffmpeg brew có bản **thiếu libass** — doctor kiểm trước, assemble tự xuống cấp xuất sub rời.
- Bridge callback = port **8100**, FastAPI = **8000** — đừng đoán port, đọc `/openapi.json`.

## Giới hạn

- Cần Chrome + extension Flow Agent (bundle trong `extension/`) connected (badge xanh) — engine chạy qua tài khoản Google thật.
- Video tốn credit Flow của tài khoản; ảnh thì không.
- AI QC được hình nhưng **không nghe audio/không xem chuyển động** — gate cuối bắt buộc người duyệt.

## License

Bộ skill vidgen-*: MIT. Phần bundle `omniflash/`, `extension/`, `cli/` lấy từ
[kodelyx/flow-agent](https://github.com/kodelyx/flow-agent) (repo gốc chưa khai báo license).

# Thư viện nhạc nền (BGM) theo mood

`assemble.py` tự chọn nhạc nền khớp `music.mood` trong `project.json`. Thư mục này là **nơi bạn
thả file nhạc**. Repo KHÔNG ship sẵn file nhạc (lý do bản quyền) — bạn tự thêm nhạc royalty-free.

## Cách assemble chọn nhạc (thứ tự ưu tiên)

1. **CLI `--bgm <file>`** — override tất cả.
2. **`music.file`** trong manifest — đường dẫn nhạc cụ thể (tương đối tính từ thư mục dự án).
3. **Auto-pick theo `music.mood`** — tìm trong thư mục này (mặc định `assets/bgm/`, đổi bằng `--bgm-dir`):
   - `assets/bgm/<mood>/*.mp3` (khuyến nghị: mỗi mood một thư mục con), HOẶC
   - `assets/bgm/<mood>*.mp3` (đặt tên file bắt đầu bằng mood).
   - Lấy file khớp **đầu tiên** (theo thứ tự chữ cái). Hỗ trợ `.mp3` và `.wav`.

## Mood vocabulary (khớp schema)

`calm` · `tense` · `uplifting` · `sad` · `epic` · `playful` · `neutral`

Ví dụ cấu trúc:
```
assets/bgm/
├── calm/       calm_piano.mp3, calm_ambient.mp3
├── uplifting/  uplifting_corporate.mp3
├── epic/       epic_trailer.mp3
└── playful/    playful_ukulele.mp3
```

## Nguồn nhạc royalty-free (tự tải, đọc kỹ license)

- **YouTube Audio Library** (studio.youtube.com → Audio Library) — miễn phí, một số cần ghi công.
- **Pixabay Music** (pixabay.com/music) — license Pixabay, phần lớn dùng thương mại không cần ghi công.
- **Free Music Archive** (freemusicarchive.org) — lọc theo CC; kiểm từng bài.
- **Incompetech** (Kevin MacLeod) — CC-BY, **phải ghi công**.
- **ccMixter** (dig.ccmixter.org) — nhạc CC cho remix/video.

> ⚠️ Luôn kiểm license từng bài trước khi dùng thương mại. Nhạc có bản quyền → video bị chặn/gỡ tiếng.

## Hoặc: TẠO nhạc/SFX bằng ElevenLabs (nếu có API key)

Môi trường này có sẵn skill:
- **`music`** — sinh nhạc nền instrumental theo mô tả (ElevenLabs Music API). Xuất `.mp3` rồi thả
  vào đúng thư mục mood, hoặc trỏ `music.file`.
- **`sound-effects`** — sinh SFX/ambience rời (nếu không dựa vào audio Veo sinh sẵn trong clip).

## Ghi chú repo

- File nhạc nặng có thể làm phình repo. Nếu không muốn version nhạc, thêm `assets/bgm/**/*.mp3`
  vào `.gitignore` và quản lý nhạc ngoài repo (trỏ `--bgm-dir`).

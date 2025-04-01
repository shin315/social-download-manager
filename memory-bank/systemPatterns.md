# System Patterns: Social Download Manager

## Kiến Trúc Hệ Thống

Social Download Manager được xây dựng theo kiến trúc mô-đun với sự phân tách rõ ràng giữa các thành phần, tuân theo mô hình MVC (Model-View-Controller) đơn giản hóa:

```
┌─────────────────────────────┐
│           UI Layer          │
│  (PyQt6 - main_window.py)   │
└───────────────┬─────────────┘
                │
                ▼
┌─────────────────────────────┐
│       Business Logic        │
│  (utils/ - downloader.py)   │
└───────────────┬─────────────┘
                │
                ▼
┌─────────────────────────────┐
│        Data Storage         │
│  (utils/ - db_manager.py)   │
└─────────────────────────────┘
```

### Cấu Trúc Thư Mục
```
social-download-manager/
  ├── main.py                  # Entry point
  ├── config.json              # User configurations
  ├── version.json             # Version information
  ├── assets/                  # Static assets
  │   ├── icon.ico
  │   ├── Logo_*.png           # App logos
  │   └── platforms/           # Platform icons
  ├── build/                   # Build artifacts
  ├── localization/            # Language support
  │   ├── english.py
  │   ├── vietnamese.py
  │   └── language_manager.py
  ├── ui/                      # UI components
  │   ├── main_window.py       # Main application window
  │   ├── video_info_tab.py    # Video download tab
  │   ├── downloaded_videos_tab.py # History tab
  │   ├── donate_tab.py        # Donation tab
  │   ├── update_dialog.py     # Update popup
  │   └── about_dialog.py      # About dialog
  └── utils/                   # Utility modules
      ├── downloader.py        # Video download logic
      ├── db_manager.py        # SQLite database operations
      ├── update_checker.py    # Version check
      ├── updater.py           # Update mechanism
      └── download_thread.py   # Threading for downloads
```

## Mẫu Thiết Kế Chính

### 1. Model-View-Controller (MVC)
- **Model**: `db_manager.py` quản lý dữ liệu và trạng thái của ứng dụng
- **View**: `ui/` chứa các thành phần giao diện người dùng
- **Controller**: `utils/downloader.py` và các module logic xử lý

### 2. Thread Worker Pattern
- Sử dụng `QThread` để tránh đóng băng UI trong khi tải xuống
- Triển khai trong `download_thread.py` để xử lý tải xuống bất đồng bộ
- Sử dụng signals và slots để giao tiếp giữa luồng tải xuống và UI

### 3. Singleton Pattern
- Áp dụng cho `db_manager.py` để đảm bảo một kết nối duy nhất đến cơ sở dữ liệu
- Áp dụng cho `language_manager.py` để quản lý tài nguyên ngôn ngữ

### 4. Factory Pattern
- Sử dụng trong `downloader.py` để tạo đối tượng downloader dựa vào loại URL
- Cho phép mở rộng dễ dàng để hỗ trợ các nền tảng mới

### 5. Observer Pattern
- UI đăng ký các callbacks để nhận thông báo về tiến trình tải xuống
- Sử dụng PyQt6 signal-slot để triển khai

## Quyết Định Kỹ Thuật Chính

### 1. Kiến Trúc Đa Tab
- Sử dụng `QTabWidget` để phân chia giao diện thành các tab chức năng riêng biệt
- Tab "Video Info" để nhập URL và tải xuống video
- Tab "Downloaded Videos" để quản lý lịch sử tải xuống
- Tab "Donate" để hiển thị thông tin ủng hộ

### 2. Cơ Sở Dữ Liệu SQLite
- Lưu trữ thông tin về video đã tải xuống
- Cấu trúc bảng đơn giản với thông tin cần thiết về video
- Cho phép tìm kiếm, lọc và quản lý video đã tải xuống

### 3. Multi-threading
- Sử dụng QThread để xử lý tải xuống ở background
- Tránh đóng băng UI khi tải xuống hoặc xử lý video
- Triển khai tải nhiều video cùng lúc (batch download)

### 4. Quốc Tế Hóa (i18n)
- Hệ thống quản lý ngôn ngữ tùy chỉnh qua `language_manager.py`
- Tách biệt văn bản UI ra khỏi mã nguồn
- Hỗ trợ tiếng Anh và tiếng Việt, dễ dàng thêm ngôn ngữ mới

### 5. FFmpeg Integration
- Sử dụng FFmpeg để xử lý chuyển đổi video sang MP3
- Kiểm tra sự tồn tại của FFmpeg trước khi cung cấp tính năng MP3
- Thiết kế dự phòng để ứng dụng vẫn hoạt động ngay cả khi FFmpeg không có

## Quan Hệ Giữa Các Thành Phần

```
┌─────────────────┐     ┌────────────────┐     ┌───────────────┐
│  MainWindow     │◄────┤ VideoInfoTab   │────►│  Downloader   │
│  (main_window)  │     │(video_info_tab)│     │ (downloader)  │
└────────┬────────┘     └────────────────┘     └───────┬───────┘
         │                                             │
         │                                             │
         ▼                                             ▼
┌─────────────────┐     ┌────────────────┐     ┌───────────────┐
│DownloadedVidsTab│────►│  DbManager     │◄────┤DownloadThread │
│(downloaded_tab) │     │ (db_manager)   │     │(downloadthread│
└─────────────────┘     └────────────────┘     └───────────────┘

┌─────────────────┐     ┌────────────────┐     ┌───────────────┐
│  UpdateDialog   │────►│ UpdateChecker  │────►│    Updater    │
│ (update_dialog) │     │(update_checker)│     │  (updater)    │
└─────────────────┘     └────────────────┘     └───────────────┘

┌─────────────────┐
│ LanguageManager │
│(language_manager│
└─────────────────┘
```

## Quy Tắc Thiết Kế

1. **Nguyên tắc Đơn Trách Nhiệm (SRP)**
   - Mỗi module có một trách nhiệm duy nhất, rõ ràng
   - `db_manager.py` chỉ xử lý thao tác với database
   - `downloader.py` chỉ xử lý logic tải video

2. **Nguyên tắc Đóng-Mở (OCP)**
   - Mở rộng để hỗ trợ các nền tảng mới không đòi hỏi thay đổi mã hiện có
   - Thiết kế factory cho downloader để dễ dàng thêm nền tảng mới

3. **Nguyên tắc Phân Tách Giao Diện (ISP)**
   - UI được chia nhỏ thành các tab và dialog riêng biệt
   - Mỗi thành phần UI chỉ phụ thuộc vào các module mà nó cần

4. **Nguyên tắc Đảo Ngược Phụ Thuộc (DIP)**
   - Các module cấp cao không phụ thuộc trực tiếp vào chi tiết triển khai
   - Sử dụng giao diện và callback để tách rời các thành phần

5. **Mẫu Messaging**
   - Sử dụng hệ thống signal/slot của PyQt6 để giao tiếp giữa các thành phần
   - Giảm sự phụ thuộc trực tiếp giữa các module 
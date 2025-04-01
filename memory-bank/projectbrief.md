# Project Brief: Social Download Manager

## Tổng Quan Dự Án
Social Download Manager (trước đây là TikTok Downloader) là ứng dụng desktop được phát triển bằng Python và PyQt6, cho phép người dùng tải video từ các nền tảng mạng xã hội mà không có watermark. Ứng dụng cung cấp giao diện thân thiện, hỗ trợ đa ngôn ngữ (tiếng Anh và tiếng Việt), và nhiều tính năng hữu ích cho người dùng cuối.

## Mục Tiêu Dự Án
1. Tạo một ứng dụng đơn giản, dễ sử dụng để tải video từ TikTok và các nền tảng khác
2. Xử lý việc tải xuống mà không có watermark
3. Hỗ trợ đa ngôn ngữ để tiếp cận nhiều người dùng hơn
4. Cung cấp các tính năng quản lý video đã tải xuống
5. Cho phép tùy chỉnh chất lượng video và định dạng tải xuống
6. Tích hợp cơ chế cập nhật tự động để người dùng luôn có phiên bản mới nhất

## Phạm Vi Dự Án
### Trong Phạm Vi:
- Tải video TikTok không watermark
- Quản lý lịch sử tải xuống 
- Hỗ trợ ngôn ngữ tiếng Anh và tiếng Việt
- Tính năng batch download (tải nhiều video cùng lúc)
- Chức năng đổi tên video trước khi tải
- Tải xuống dưới dạng audio (MP3)
- Kiểm tra và cập nhật phiên bản tự động
- Giao diện dark/light mode

### Ngoài Phạm Vi:
- Khả năng chỉnh sửa video
- Tính năng upload video lên các nền tảng
- Hỗ trợ các nền tảng không phổ biến

## Công Nghệ Chính
- Python 3.8+
- PyQt6 cho giao diện người dùng
- SQLite cho lưu trữ dữ liệu
- FFmpeg cho xử lý audio
- PyInstaller để đóng gói ứng dụng

## Yêu Cầu Kỹ Thuật
- Giao diện người dùng đơn giản, trực quan
- Đa ngôn ngữ được tích hợp xuyên suốt ứng dụng
- Quản lý lịch sử tải video với khả năng tìm kiếm và lọc
- Cơ chế kiểm tra và cập nhật phiên bản tự động
- Hỗ trợ cả hai chế độ sáng/tối (light/dark mode)
- Đóng gói thành ứng dụng có thể cài đặt trên Windows

## Các Mốc Quan Trọng
- ✅ Phiên bản 1.0: Ra mắt với tên TikTok Downloader
- ✅ Phiên bản 1.1: Đổi tên thành Social Download Manager, cải thiện UI/UX
- ✅ Phiên bản 1.1.2: Thêm tính năng kiểm tra FFmpeg
- ✅ Phiên bản 1.1.3: Cải thiện cấu hình cho file .exe
- ✅ Phiên bản 1.1.4: Thay đổi logo và sửa lỗi hiển thị icon
- 🔲 Phiên bản 2.0: Mở rộng hỗ trợ các nền tảng mạng xã hội khác 
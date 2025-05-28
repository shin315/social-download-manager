# Tech Context: Social Download Manager

## Ngôn Ngữ và Framework Chính

### Python 3.8+
- Ngôn ngữ chính để phát triển toàn bộ ứng dụng
- Ưu điểm: dễ đọc, phát triển nhanh, nhiều thư viện hỗ trợ
- Được sử dụng cho cả logic nghiệp vụ và tích hợp UI

### PyQt6
- Framework UI chính cho giao diện người dùng
- Cung cấp các widget hiện đại và khả năng tùy biến cao
- Hỗ trợ cả light/dark mode thông qua CSS
- Sử dụng hệ thống signal/slot cho giao tiếp giữa các thành phần

### SQLite
- Cơ sở dữ liệu nhẹ để lưu trữ thông tin video đã tải xuống
- Không cần cài đặt server database riêng
- Cả database được lưu trong một file duy nhất
- Triển khai thông qua module `sqlite3` built-in của Python

## Công Nghệ Và Thư Viện

### yt-dlp
- Thư viện tải xuống video từ nhiều nền tảng trực tuyến
- Fork của youtube-dl với nhiều cải tiến về hiệu suất
- Hỗ trợ tải từ TikTok và nhiều nền tảng khác mà không có watermark
- Liên tục được cập nhật để đối phó với thay đổi API của các nền tảng
- Phiên bản hiện tại: 2025.3.31

### FFmpeg
- Công cụ xử lý âm thanh và video mạnh mẽ
- Được sử dụng để chuyển đổi video sang MP3
- Chạy như một công cụ command-line bên ngoài
- Yêu cầu người dùng cài đặt riêng (không đóng gói cùng ứng dụng)
- Trong phiên bản 1.2.1, đã cải thiện việc ẩn cửa sổ cmd khi chạy ffmpeg trên Windows

### Requests
- Thư viện HTTP cho Python, sử dụng cho các yêu cầu mạng
- Được sử dụng để kiểm tra cập nhật và tải bản cập nhật
- Xử lý API requests đến các nguồn tài nguyên và URL

### PyInstaller
- Công cụ đóng gói ứng dụng Python thành file thực thi (.exe)
- Đóng gói tất cả các dependencies vào một file duy nhất
- Sử dụng file spec (.spec) để cấu hình quá trình build
- Hỗ trợ đóng gói tài nguyên (hình ảnh, icon, v.v.)

## Môi Trường Phát Triển

### IDE
- Phát triển chủ yếu trên Visual Studio Code hoặc PyCharm
- Sử dụng các extension Python, PyQt và Git

### Hệ Điều Hành
- Phát triển chủ yếu trên Windows
- Ứng dụng hỗ trợ:
  - Windows 10+
  - macOS (thông qua cài đặt Python và dependencies)
  - Linux (thông qua cài đặt Python và dependencies)

### Version Control
- Git cho quản lý mã nguồn
- GitHub cho lưu trữ repo và phát hành bản cập nhật
- Các release được tag và xuất bản qua GitHub Releases

## Yêu Cầu Kỹ Thuật

### Phần Cứng Tối Thiểu
- CPU: 1 GHz hoặc nhanh hơn
- RAM: 1 GB (2 GB khuyến nghị)
- Đĩa cứng: 100 MB trống (không bao gồm không gian lưu trữ video)
- Kết nối internet để tải video và kiểm tra cập nhật

### Phần Mềm Yêu Cầu
- Với bản cài đặt (.exe): Không yêu cầu thêm (tất cả được đóng gói)
- Với mã nguồn:
  - Python 3.8+
  - Các thư viện trong requirements.txt
  - FFmpeg (tùy chọn, cho chức năng MP3)

## Cấu Trúc Database

### Bảng `downloads`
```sql
CREATE TABLE downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT,
    title TEXT,
    creator TEXT,
    custom_name TEXT,
    platform TEXT,
    quality TEXT,
    format TEXT,
    thumbnail TEXT,
    file_path TEXT,
    file_size INTEGER,
    download_date TEXT,
    hashtags TEXT
);
```

## Giới Hạn Kỹ Thuật

### Hạn Chế API
- Phụ thuộc vào API của các nền tảng mạng xã hội
- Có thể bị ảnh hưởng nếu các nền tảng thay đổi cấu trúc trang hoặc API
- Cần cập nhật thường xuyên để theo kịp các thay đổi
- Phiên bản 1.2.1 đã cải thiện xử lý lỗi "connection reset" khi gọi API TikTok

### Xử Lý Đồng Thời
- Số lượng tải xuống đồng thời bị giới hạn để tránh quá tải
- Người dùng có thể gặp giới hạn request nếu tải quá nhiều video cùng lúc

### Hỗ Trợ Nền Tảng
- Hiện tại chỉ hỗ trợ đầy đủ TikTok
- Các nền tảng khác sẽ được bổ sung dần trong phiên bản 2.0

## Quy Trình Cập Nhật

### Kiểm Tra Cập Nhật
- Ứng dụng kiểm tra version.json từ GitHub khi khởi động
- So sánh phiên bản hiện tại (1.2.1) với phiên bản mới nhất
- Hiển thị thông báo cập nhật nếu có phiên bản mới

### Quy Trình Cập Nhật
1. Tải bản cập nhật từ GitHub Releases
2. Giải nén tự động
3. Thay thế file hiện tại
4. Khởi động lại ứng dụng

## Cân Nhắc Bảo Mật

### Xử Lý URL
- Sanitize URLs trước khi xử lý để tránh command injection
- Kiểm tra tính hợp lệ của URL thông qua regular expression

### Tải Xuống An Toàn
- Quét các file tải xuống để đảm bảo không có mã độc
- Sử dụng các thư viện an toàn và được duy trì tích cực

### Cập Nhật Ứng Dụng
- Tải cập nhật chỉ từ nguồn chính thức (GitHub Repository)
- Kiểm tra tính toàn vẹn của file cập nhật trước khi cài đặt

## Cải Tiến Kỹ Thuật Trong Phiên Bản 1.2.1

### Cải Thiện Xử Lý Lỗi
- Thêm xử lý lỗi "connection reset" khi gọi API TikTok
- Cải thiện cơ chế retry và báo cáo lỗi
- Thêm logging chi tiết hơn để hỗ trợ debugging

### Tối Ưu Môi Trường Đóng Gói
- Thêm phát hiện môi trường đóng gói (frozen) để tắt logging không cần thiết
- Sử dụng `getattr(sys, 'frozen', False)` để kiểm tra nếu đang chạy từ file exe
- Tránh tạo file log gerror.log và app_debug.log trong môi trường sản phẩm

### Cải Thiện UX
- Ẩn cửa sổ cmd khi chạy ffmpeg trên Windows bằng cách sử dụng `creationflags=0x08000000` (CREATE_NO_WINDOW)
- Sửa lỗi sắp xếp trong Downloaded Videos tab
- Tối ưu hóa kích thước cột cho ngôn ngữ tiếng Việt 
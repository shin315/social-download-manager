# Active Context: Social Download Manager

## Tình Trạng Hiện Tại
Social Download Manager hiện đang ở phiên bản 1.2.0 với các tính năng cốt lõi đã hoạt động tốt cho nền tảng TikTok. Phiên bản 1.2 bổ sung nhiều cải tiến về giao diện người dùng, tối ưu hóa hiển thị đa ngôn ngữ, và sửa các lỗi quan trọng. Giai đoạn tiếp theo đang hướng tới phiên bản 2.0 với mục tiêu mở rộng hỗ trợ cho nhiều nền tảng mạng xã hội khác.

## Trọng Tâm Hiện Tại
1. **Mở rộng hỗ trợ đa nền tảng**:
   - Nghiên cứu và triển khai hỗ trợ cho YouTube
   - Tích hợp Instagram downloader
   - Thêm hỗ trợ cho Facebook và Twitter
   - Xây dựng cấu trúc mở rộng dễ dàng thêm nền tảng mới

2. **Cải thiện trải nghiệm người dùng**:
   - Cải tiến giao diện để dễ dàng chuyển đổi giữa các nền tảng
   - Thêm biểu tượng và nhận dạng tự động cho các URL khác nhau
   - Nâng cấp hệ thống hiển thị thông tin video cho mỗi nền tảng
   - Tối ưu hóa quy trình batch download

3. **Tối ưu hóa hiệu suất**:
   - Cải thiện tốc độ tải xuống bằng cách tối ưu requests
   - Giảm thiểu thời gian phân tích và xử lý URL
   - Cải thiện hiệu suất quản lý database với số lượng video lớn

## Quyết Định Kỹ Thuật Đang Cân Nhắc

### Kiến Trúc Hỗ Trợ Đa Nền Tảng
```
┌─────────────────┐
│ Platform Factory │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │ TikTok  │  │ YouTube │  │ Instagram   │  │
│  │ Handler │  │ Handler │  │ Handler     │  │
│  └─────────┘  └─────────┘  └─────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

Cân nhắc giữa hai phương pháp:
1. **Factory Method Pattern**: Tạo một PlatformHandlerFactory trả về handler phù hợp dựa trên URL
2. **Strategy Pattern**: Tạo các strategy khác nhau cho mỗi nền tảng, dễ dàng chuyển đổi giữa chúng

### UI cho Đa Nền Tảng
Đang cân nhắc hai thiết kế:
1. **Tab-based**: Mỗi nền tảng một tab riêng biệt với UI tùy chỉnh
2. **Unified Interface**: Một giao diện thống nhất với dropdown chọn nền tảng

Hướng hiện tại: Sử dụng unified interface với các thành phần UI động thay đổi theo nền tảng được chọn.

## Thay Đổi Gần Đây

### Cải Thiện Trải Nghiệm Người Dùng (v1.2.0)
- Tối ưu hóa kích thước cột cho hiển thị đa ngôn ngữ, đặc biệt là tiếng Việt
- Sửa lỗi hiển thị cửa sổ CMD khi mở thư mục chứa file, sử dụng subprocess với CREATE_NO_WINDOW
- Bỏ mặc định chọn "Delete from disk" khi xóa video để tránh xóa nhầm
- Cải thiện sắp xếp video trong tab Downloaded Videos

### Thay Đổi Logo (v1.1.4)
- Đã thay thế logo cũ bằng logo mới với ba kích thước (16x16, 32x32, 70x70)
- Cập nhật hiển thị logo trong cả hai chế độ sáng/tối
- Logo mới có thiết kế hiện đại và phù hợp hơn

### Sửa Lỗi Hiển Thị Icon (v1.1.4)
- Đã giải quyết vấn đề hiển thị icon khi đóng gói thành EXE
- Thêm hàm `get_resource_path()` để xử lý đường dẫn tài nguyên đúng cách
- Cập nhật tất cả đường dẫn tĩnh để đảm bảo tìm thấy tài nguyên khi đóng gói

### Cải Thiện Build System (v1.1.4)
- Tạo công cụ build.py tự động
- Cấu hình đầy đủ tất cả tài nguyên cần thiết trong file .spec
- Tự động cài đặt PyInstaller nếu cần thiết

## Nhiệm Vụ Tiếp Theo

### Ưu Tiên Cao
1. **Thiết kế Factory Pattern cho các nền tảng**:
   - Tạo cấu trúc cơ bản cho `platform_handler.py`
   - Định nghĩa interface chung cho tất cả các handler
   - Triển khai mẫu cho YouTube và Instagram

2. **Xây dựng YouTube downloader**:
   - Tích hợp yt-dlp cho YouTube
   - Hỗ trợ lựa chọn chất lượng và định dạng video
   - Xử lý playlist và video riêng lẻ

3. **Cập nhật UI cho đa nền tảng**:
   - Thiết kế selector cho nền tảng
   - Tạo biểu tượng cho mỗi nền tảng
   - Điều chỉnh hiển thị metadata theo nền tảng

### Ưu Tiên Trung Bình
1. **Cải thiện database schema**:
   - Thêm trường để lưu trữ metadata đặc thù của từng nền tảng
   - Tối ưu hóa truy vấn cho số lượng video lớn

2. **Nâng cấp hệ thống tìm kiếm và lọc**:
   - Thêm bộ lọc theo nền tảng
   - Cải thiện tìm kiếm toàn văn trên metadata

3. **Bổ sung tiện ích xử lý video**:
   - Thêm công cụ cắt video cơ bản
   - Hỗ trợ trích xuất thumbnail

### Ưu Tiên Thấp
1. **Cải thiện cấu hình người dùng**:
   - Thêm tùy chọn cấu hình cho mỗi nền tảng
   - Lưu thư mục đầu ra riêng cho từng nền tảng

2. **Hỗ trợ thêm ngôn ngữ**:
   - Chuẩn bị cấu trúc để thêm ngôn ngữ khác
   - Cập nhật chuỗi cho tính năng mới

## Đang Chờ Phát Triển
- Triển khai Instagram downloader
- Thêm hỗ trợ cho Facebook và Twitter
- Nâng cấp hệ thống cập nhật để hỗ trợ cập nhật tăng dần 
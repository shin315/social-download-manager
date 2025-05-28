# Active Context: Social Download Manager

## Tình Trạng Hiện Tại
Social Download Manager hiện đang ở phiên bản 1.2.1 với các tính năng cốt lõi đã hoạt động tốt cho nền tảng TikTok. Phiên bản 1.2.1 tập trung vào việc sửa lỗi kết nối và cải thiện trải nghiệm người dùng khi tải video TikTok và chuyển đổi sang MP3. Giai đoạn tiếp theo đang hướng tới phiên bản 2.0 với mục tiêu mở rộng hỗ trợ cho nhiều nền tảng mạng xã hội khác.

## Trọng Tâm Hiện Tại
1. **Mở rộng hỗ trợ đa nền tảng**:
   - Nghiên cứu và triển khai hỗ trợ cho YouTube
   - Tích hợp Instagram downloader
   - Thêm hỗ trợ cho Facebook và Twitter
   - Xây dựng cấu trúc mở rộng dễ dàng thêm nền tảng mới

2. **Cải thiện tab Downloaded Videos**:
   - Thiết kế và triển khai bộ chọn platform bằng QComboBox
   - Thêm cột Platform vào thông tin cố định hiển thị với icon
   - Cải tiến bảng hiển thị động theo nền tảng được chọn
   - Cập nhật phần chi tiết video để hiển thị thông tin đặc trưng cho mỗi platform

3. **Cải thiện trải nghiệm người dùng**:
   - Cải tiến giao diện để dễ dàng chuyển đổi giữa các nền tảng
   - Thêm biểu tượng và nhận dạng tự động cho các URL khác nhau
   - Nâng cấp hệ thống hiển thị thông tin video cho mỗi nền tảng
   - Tối ưu hóa quy trình batch download

4. **Tối ưu hóa hiệu suất**:
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
Đã quyết định thiết kế UI cho Downloaded Videos tab:
1. **Cột cố định cho tất cả platform**:
   - Checkbox chọn, Platform, Title, Creator/Channel, Quality, Format, Duration, Size, Date download
2. **Cột động theo platform**:
   - YouTube: thêm Playlist, Release Date
   - TikTok: thêm Hashtags
3. **Bộ chọn platform** bằng QComboBox đặt cạnh tab Downloaded Videos

## Thay Đổi Gần Đây

### Cải Thiện Xử Lý Lỗi Kết Nối (v1.2.1)
- Đã sửa lỗi "connection reset" khi tải video TikTok trong điều kiện mạng không ổn định
- Cải thiện cơ chế xử lý lỗi khi có vấn đề về mạng
- Thêm logging chi tiết hơn cho các lỗi tải xuống
- Sửa lỗi cửa sổ cmd chớp nháy khi chuyển đổi sang MP3 bằng ffmpeg
- Thêm cơ chế phát hiện môi trường đóng gói để tắt logging không cần thiết

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

## Nhiệm Vụ Tiếp Theo

### Ưu Tiên Cao
1. **Cải tiến tab Downloaded Videos**:
   - Thêm QComboBox cho lựa chọn platform
   - Thêm cột Platform với icon vào bảng
   - Triển khai hiển thị bảng động theo platform được chọn
   - Cập nhật phần chi tiết video để hiển thị thông tin platform-specific

2. **Thiết kế Factory Pattern cho các nền tảng**:
   - Tạo cấu trúc cơ bản cho `platform_handler.py`
   - Định nghĩa interface chung cho tất cả các handler
   - Triển khai mẫu cho YouTube và Instagram

3. **Xây dựng YouTube downloader**:
   - Tích hợp yt-dlp cho YouTube
   - Hỗ trợ lựa chọn chất lượng và định dạng video
   - Xử lý playlist và video riêng lẻ

### Ưu Tiên Trung Bình
1. **Cải thiện database schema**:
   - Thêm trường platform để phân loại video
   - Thêm trường để lưu trữ metadata đặc thù của từng nền tảng
   - Tối ưu hóa truy vấn cho số lượng video lớn

2. **Nâng cấp hệ thống tìm kiếm và lọc**:
   - Cập nhật bộ lọc cho các cột mới (Platform, Playlist, Release Date)
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
from PIL import Image
import os

# Đường dẫn đến file logo.png
logo_path = os.path.join('assets', 'logo.png')
ico_path = os.path.join('assets', 'app_icon.ico')

try:
    # Mở file ảnh
    img = Image.open(logo_path)
    
    # Tạo danh sách các kích thước icon cho Windows
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # Lưu file ico với nhiều kích thước
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    
    print(f"Đã tạo file icon thành công: {ico_path}")
except Exception as e:
    print(f"Lỗi khi tạo file icon: {e}") 
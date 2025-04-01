import sys
import logging
import logging.handlers
import os
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

# Kiểm tra xem có đang chạy từ file EXE hay không
def is_packaged():
    """Check if the application is running from a packaged executable"""
    return getattr(sys, 'frozen', False)

# Thiết lập logging nâng cao
def setup_enhanced_logging():
    """Set up detailed logging for better debugging"""
    # Chỉ thiết lập logging đầy đủ khi chạy từ mã nguồn, không phải từ file đóng gói
    if is_packaged():
        # Thiết lập logging tối thiểu khi chạy từ file đóng gói
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.ERROR)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        root_logger.addHandler(console_handler)
        return root_logger
        
    # Tạo formatter với thông tin chi tiết hơn
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # File handler with rotation để tránh file log quá lớn
    file_handler = logging.handlers.RotatingFileHandler(
        "app_debug.log", 
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    
    # API error log riêng biệt
    api_error_handler = logging.FileHandler("api_errors.log")
    api_error_handler.setFormatter(log_formatter)
    api_error_handler.setLevel(logging.ERROR)
    
    # Add API-related filter
    class APIErrorFilter(logging.Filter):
        def filter(self, record):
            msg = record.getMessage().lower()
            return "api" in msg or "yt-dlp" in msg or "tiktok" in msg
    
    api_error_handler.addFilter(APIErrorFilter())
    
    # Cấu hình root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(api_error_handler)
    
    return root_logger

# Khởi tạo logger
logger = setup_enhanced_logging()

def main():
    msg = "=== Starting Social Download Manager ==="
    if not is_packaged():
        logger.info(msg)
    try:
        # Check if any command line arguments are present
        if len(sys.argv) > 1 and not is_packaged():
            logger.info(f"Command line arguments: {sys.argv[1:]}")
        
        app = QApplication(sys.argv)
        if not is_packaged():
            logger.info("Created QApplication")
        window = MainWindow()
        if not is_packaged():
            logger.info("Created MainWindow")
        window.show()
        if not is_packaged():
            logger.info("MainWindow showed")
        sys.exit(app.exec())
    except Exception as e:
        if not is_packaged():
            logger.exception(f"Error during startup: {e}")
        else:
            print(f"Error during startup: {e}")


if __name__ == "__main__":
    main() 
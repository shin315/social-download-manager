import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

# Thiết lập logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app_debug.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("=== Starting Social Download Manager ===")
    try:
        app = QApplication(sys.argv)
        logger.info("Created QApplication")
        window = MainWindow()
        logger.info("Created MainWindow")
        window.show()
        logger.info("MainWindow showed")
        sys.exit(app.exec())
    except Exception as e:
        logger.exception(f"Error during startup: {e}")


if __name__ == "__main__":
    main() 
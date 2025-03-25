#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Language manager for TikTok Downloader
"""

import importlib
import os
import json
from localization import english, vietnamese

# Đường dẫn đến file cấu hình
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

class LanguageManager:
    """Quản lý ngôn ngữ trong ứng dụng"""
    
    def __init__(self):
        self.languages = {
            "english": english,
            "vietnamese": vietnamese
        }
        self.current_language = self.load_language_from_config()
        
    def load_language_from_config(self):
        """Tải cài đặt ngôn ngữ từ file cấu hình"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    language = config.get('language', 'english')
                    if language in self.languages:
                        return language
            return "english"  # Mặc định là tiếng Anh
        except Exception as e:
            print(f"Error loading language from config: {e}")
            return "english"
    
    def save_language_to_config(self, language):
        """Lưu cài đặt ngôn ngữ vào file cấu hình"""
        try:
            # Tạo file config nếu chưa tồn tại
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            
            # Cập nhật ngôn ngữ
            config['language'] = language
            
            # Lưu cấu hình
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving language to config: {e}")
    
    def set_language(self, language):
        """Thiết lập ngôn ngữ hiện tại"""
        if language in self.languages:
            self.current_language = language
            self.save_language_to_config(language)
            return True
        return False
    
    def get_text(self, key):
        """Lấy chuỗi văn bản theo key và ngôn ngữ hiện tại"""
        lang_module = self.languages.get(self.current_language, english)
        if hasattr(lang_module, key):
            return getattr(lang_module, key)
        # Fallback to English if the key does not exist in the current language
        if hasattr(english, key):
            return getattr(english, key)
        # Return the key itself if not found in any language
        return key
    
    def tr(self, key):
        """Alias cho get_text để dịch key theo ngôn ngữ hiện tại"""
        return self.get_text(key)
    
    def get_available_languages(self):
        """Lấy danh sách các ngôn ngữ có sẵn"""
        return {code: module.LANGUAGE_NAME for code, module in self.languages.items()}
    
    def get_current_language_name(self):
        """Lấy tên của ngôn ngữ hiện tại"""
        return self.languages[self.current_language].LANGUAGE_NAME

    def create_sample_data(self):
        """Tạo dữ liệu mẫu cho demo"""
        # Lưu toàn bộ danh sách video (để thống kê)
        self.all_videos = [
            # ... danh sách 12 video như cũ ...
        ]
        
        # Chỉ hiển thị 8 video đầu tiên khi lọc
        self.filtered_videos = self.all_videos[:8]

    def filter_videos(self):
        """Lọc video theo từ khóa tìm kiếm"""
        search_text = self.search_input.text().lower()
        
        if search_text:
            # Lọc theo từ khóa
            self.filtered_videos = [
                video for video in self.all_videos
                if search_text in video[0].lower() or search_text in video[7].lower()
            ]
        else:
            # Nếu không có từ khóa, hiển thị tất cả (vẫn giới hạn 8 video)
            self.filtered_videos = self.all_videos[:8]
        
        # Cập nhật bảng
        self.refresh_filtered_videos()

# Singleton instance
_instance = None

def get_instance():
    """Lấy instance của LanguageManager (Singleton pattern)"""
    global _instance
    if _instance is None:
        _instance = LanguageManager()
    return _instance 
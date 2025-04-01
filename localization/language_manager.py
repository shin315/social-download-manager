#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Language manager for Social Download Manager
"""

import importlib
import os
import json
from localization import english, vietnamese

# Path to configuration file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')

class LanguageManager:
    """Application language manager"""
    
    def __init__(self):
        self.languages = {
            "english": english,
            "vietnamese": vietnamese
        }
        self.current_language = self.load_language_from_config()
        
    def load_language_from_config(self):
        """Load language settings from configuration file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    language = config.get('language', 'english')
                    if language in self.languages:
                        return language
            return "english"  # Default is English
        except Exception as e:
            print(f"Error loading language from config: {e}")
            return "english"
    
    def save_language_to_config(self, language):
        """Save language settings to configuration file"""
        try:
            # Create config file if it doesn't exist
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            
            # Update language
            config['language'] = language
            
            # Save configuration
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving language to config: {e}")
    
    def set_language(self, language):
        """Set current language"""
        if language in self.languages:
            self.current_language = language
            self.save_language_to_config(language)
            return True
        return False
    
    def get_text(self, key):
        """Get text string by key in current language"""
        lang_module = self.languages.get(self.current_language, english)
        if hasattr(lang_module, key):
            return getattr(lang_module, key)
        # Fallback to English if the key does not exist in the current language
        if hasattr(english, key):
            return getattr(english, key)
        # Return the key itself if not found in any language
        return key
    
    def tr(self, key):
        """Alias for get_text to translate key in current language"""
        return self.get_text(key)
    
    def get_available_languages(self):
        """Get list of available languages"""
        return {code: module.LANGUAGE_NAME for code, module in self.languages.items()}
    
    def get_current_language_name(self):
        """Get name of current language"""
        return self.languages[self.current_language].LANGUAGE_NAME

    def create_sample_data(self):
        """Create sample data for demo"""
        # Store full video list (for statistics)
        self.all_videos = [
            # ... list of 12 videos as before ...
        ]
        
        # Only display first 8 videos when filtering
        self.filtered_videos = self.all_videos[:8]

    def filter_videos(self):
        """Filter videos by search keyword"""
        search_text = self.search_input.text().lower()
        
        if search_text:
            # Filter by keyword
            self.filtered_videos = [
                video for video in self.all_videos
                if search_text in video[0].lower() or search_text in video[7].lower()
            ]
        else:
            # If no keyword, display all (still limited to 8 videos)
            self.filtered_videos = self.all_videos[:8]
        
        # Update table
        self.refresh_filtered_videos()

# Singleton instance
_instance = None

def get_instance():
    """Get instance of LanguageManager (Singleton pattern)"""
    global _instance
    if _instance is None:
        _instance = LanguageManager()
    return _instance 
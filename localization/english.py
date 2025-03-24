#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
English language file for SoDownloader
"""

# Common strings
LANGUAGE_NAME = "English"

# Menu bar
MENU_FILE = "File"
MENU_APPEARANCE = "Appearance"
MENU_LANGUAGE = "Language"
MENU_PLATFORM = "Platform"
MENU_HELP = "Help"
MENU_BUY_COFFEE = "Buy Me A Coffee"

# File menu items
MENU_CHOOSE_FOLDER = "Choose Output Folder"
MENU_EXIT = "Exit"

# Appearance menu items
MENU_DARK_MODE = "Dark Mode"
MENU_LIGHT_MODE = "Light Mode"

# Help menu items
MENU_ABOUT = "About"
MENU_CHECK_UPDATES = "Check for Updates"

# Platform menu items
PLATFORM_TIKTOK = "TikTok"
PLATFORM_YOUTUBE = "YouTube (Coming Soon)"
PLATFORM_INSTAGRAM = "Instagram (Coming Soon)"
PLATFORM_FACEBOOK = "Facebook (Coming Soon)"

# Tab names
TAB_VIDEO_INFO = "Video Info"
TAB_DOWNLOADED_VIDEOS = "Downloaded Videos"

# Video Info tab
LABEL_VIDEO_URL = "Video URL:"
PLACEHOLDER_VIDEO_URL = "Enter TikTok URL(s) - separate multiple URLs with spaces"
BUTTON_GET_INFO = "Get Info"
LABEL_OUTPUT_FOLDER = "Output folder:"
PLACEHOLDER_OUTPUT_FOLDER = "Choose an output folder..."
BUTTON_CHOOSE_FOLDER = "Choose Folder"
BUTTON_SELECT_ALL = "Select All"
BUTTON_UNSELECT_ALL = "Unselect All"
BUTTON_DELETE_ALL = "Delete All"
BUTTON_DOWNLOAD = "Download"

# Video table headers
HEADER_SELECT = "Select"
HEADER_VIDEO_TITLE = "Video Title"
HEADER_CREATOR = "Creator"
HEADER_QUALITY = "Quality"
HEADER_FORMAT = "Format"
HEADER_DURATION = "Duration"
HEADER_SIZE = "Size"
HEADER_CAPTION = "Caption"
HEADER_HASHTAGS = "Hashtags"
HEADER_ACTION = "Action"
HEADER_ACTIONS = "Actions"
HEADER_STATUS = "Status"
HEADER_DOWNLOAD_DATE = "Download Date"
HEADER_DATE = "Date"
HEADER_SAVED_FOLDER = "Saved Folder"
HEADER_TITLE = "Title"

# Downloaded Videos tab
LABEL_SEARCH = "Search:"
PLACEHOLDER_SEARCH = "Search downloaded videos..."
BUTTON_REFRESH = "Refresh"
LABEL_TOTAL_VIDEOS = "Total videos: {}"
LABEL_TOTAL_SIZE = "Total size: {}"
LABEL_LAST_DOWNLOAD = "Last download: {}"
LABEL_DOWNLOAD_SUCCESS_RATE = "Success rate: {}%"

# Buttons
BUTTON_OPEN = "Open"
BUTTON_DELETE = "Delete"
BUTTON_DELETE_SELECTED = "Delete Selected"
BUTTON_OPEN_FOLDER = "Open Folder"
BUTTON_CANCEL = "Cancel"
BUTTON_OK = "OK"
BUTTON_COPY = "Copy"

# Quality options
QUALITY_1080P = "1080p"
QUALITY_720P = "720p"
QUALITY_480P = "480p"
QUALITY_360P = "360p"
QUALITY_320KBPS = "320kbps"
QUALITY_192KBPS = "192kbps"
QUALITY_128KBPS = "128kbps"

# Format options
FORMAT_VIDEO_MP4 = "MP4"
FORMAT_AUDIO_MP3 = "MP3"

# Status messages
STATUS_READY = "Ready"
STATUS_FOLDER_SET = "Save folder set to: {}"
STATUS_DOWNLOAD_SUCCESS = "Successful"
STATUS_DOWNLOAD_SUCCESS_WITH_FILENAME = "Downloaded: {}"
STATUS_DOWNLOAD_FAILED = "Download failed"
STATUS_VIDEO_INFO = "Video information retrieved successfully"
STATUS_DELETED = "Deleted: {}"
STATUS_VIDEOS_REFRESHED = "Videos list refreshed"
STATUS_LANGUAGE_CHANGED = "Language changed to: {}"
STATUS_DOWNLOADING_SHORT = "Downloading..."
STATUS_GETTING_INFO_SHORT = "Getting info..."
STATUS_GETTING_INFO_MULTIPLE = "Getting info for {} videos..."
STATUS_VIDEOS_LOADED = "Loaded info for {} videos"
STATUS_DOWNLOADING_WITH_TITLE = "Downloading: {}"
STATUS_DOWNLOADING_MULTIPLE = "Downloading {} videos..."
STATUS_DOWNLOADING_REMAINING = "Downloading {} remaining videos..."
STATUS_ONE_OF_MULTIPLE_DONE = "Downloaded: {}. {} videos still downloading..."
STATUS_SELECTED_DELETED = "Deleted {} selected videos"
STATUS_REFRESH_ERROR = "Error refreshing videos list"
STATUS_ADD_VIDEO_ERROR = "Error adding video"
STATUS_VIDEO_ADDED = "Video added to list"
STATUS_DARK_MODE_ENABLED = "Dark mode enabled"
STATUS_LIGHT_MODE_ENABLED = "Light mode enabled"
STATUS_ERROR = "Error: {}"
STATUS_DOWNLOADING_PROGRESS = "{}% - {}"
STATUS_VIDEOS_ALREADY_EXIST = "All selected videos already exist"
STATUS_DOWNLOAD_CANCELLED = "Download cancelled"
STATUS_COPIED = "Copied to clipboard"
STATUS_ALL_VIDEOS_SELECTED = "All videos selected"
STATUS_ALL_VIDEOS_UNSELECTED = "All videos unselected"
STATUS_NO_VIDEOS_SELECTED = "No videos selected"
STATUS_VIDEOS_DELETED = "{} videos deleted successfully"
STATUS_DOWNLOADED_VIDEOS_LOADED = "Loaded {} videos from database"
STATUS_NO_DOWNLOADS = "No downloads found in database"
STATUS_NO_NEW_URLS = "All URLs already exist in the list"

# Dialogs
DIALOG_CONFIRM_DELETION = "Confirm Deletion"
DIALOG_CONFIRM_DELETE_ALL = "Are you sure you want to delete all videos?"
DIALOG_CONFIRM_DELETE_VIDEO = "Are you sure you want to delete the video:\n'{}'"
DIALOG_CONFIRM_DELETE_SELECTED = "Are you sure you want to delete {} selected videos?"
DIALOG_ERROR = "Error"
DIALOG_NO_VIDEOS = "No videos to download"
DIALOG_NO_VIDEOS_SELECTED = "No videos selected"
DIALOG_NO_OUTPUT_FOLDER = "Please select an output folder"
DIALOG_FOLDER_NOT_FOUND = "Folder not found:\n{}"
DIALOG_CANNOT_OPEN_FOLDER = "Cannot open folder:\n{}"
DIALOG_DOWNLOAD_STARTED = "Download Started"
DIALOG_DOWNLOAD_STARTED_MSG = "Download started.\nThis is a demo interface, download functionality will be implemented with yt-dlp."
DIALOG_COMING_SOON = "Coming Soon"
DIALOG_FEATURE_DEVELOPING = "This feature is under development."
DIALOG_DOWNLOAD_SUCCESS = "Successfully downloaded:\n{}"
DIALOG_DOWNLOAD_MULTIPLE_SUCCESS = "Successfully downloaded {} videos"
DIALOG_DOWNLOAD_SUCCESS_LOCATION = "File saved at {}"
DIALOG_UNSUPPORTED_CONTENT = "Unsupported content. Only TikTok videos are supported."
DIALOG_VIDEOS_EXIST = "Videos Already Exist"
DIALOG_VIDEOS_ALREADY_EXIST = "The following videos already exist and will not be downloaded again:"
DIALOG_FILE_EXISTS = "File Already Exists"
DIALOG_FILE_EXISTS_MESSAGE = "The file '{}' already exists in the output folder.\nDo you want to overwrite it?"

# About dialog
ABOUT_TITLE = "About SoDownloader"
ABOUT_MESSAGE = "SoDownloader v1.0\n\nA simple application to download videos without watermark from multiple platforms."

# Video details
DETAIL_QUALITY = "Quality"
DETAIL_FORMAT = "Format"
DETAIL_DURATION = "Duration"
DETAIL_SIZE = "Size"
DETAIL_DOWNLOADED = "Downloaded"
DETAIL_STATUS = "Status"

# Donate area
DONATE_TITLE = "Support Me"
DONATE_DESC = "This tool is completely free, but if you find it useful, please consider buying me a coffee!"
DONATE_QR_LABEL = "Scan MOMO QR"
DONATE_COFFEE_LINK = "Buy Me A Coffee"
DONATE_AREA_TITLE = "Support Area" 
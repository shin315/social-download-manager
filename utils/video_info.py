class VideoInfo:
    """Class for storing video information across different platforms"""
    
    def __init__(self):
        # Basic info
        self.title = "Unknown Title"
        self.url = ""
        self.thumbnail = ""
        self.duration = 0
        self.formats = []
        
        # Creator info
        self.creator = "Unknown"
        self.creator_url = ""
        
        # Content info
        self.caption = ""
        self.description = ""
        self.hashtags = []
        
        # Stats
        self.like_count = 0
        self.view_count = 0
        self.comment_count = 0
        
        # Platform specific
        self.platform = ""
        self.platform_id = ""
        
        # Additional fields for specific platforms can be stored in this dict
        self.platform_data = {}
        
    def __str__(self):
        """String representation for debugging"""
        return f"VideoInfo(title='{self.title}', platform='{self.platform}', url='{self.url}', duration={self.duration}, formats_count={len(self.formats)})"
        
    def copy(self):
        """Create a copy of this VideoInfo"""
        new_info = VideoInfo()
        
        # Copy basic info
        new_info.title = self.title
        new_info.url = self.url
        new_info.thumbnail = self.thumbnail
        new_info.duration = self.duration
        new_info.formats = self.formats.copy() if self.formats else []
        
        # Copy creator info
        new_info.creator = self.creator
        new_info.creator_url = self.creator_url
        
        # Copy content info
        new_info.caption = self.caption
        new_info.description = self.description
        new_info.hashtags = self.hashtags.copy() if self.hashtags else []
        
        # Copy stats
        new_info.like_count = self.like_count
        new_info.view_count = self.view_count
        new_info.comment_count = self.comment_count
        
        # Copy platform info
        new_info.platform = self.platform
        new_info.platform_id = self.platform_id
        
        # Copy platform-specific data
        new_info.platform_data = self.platform_data.copy() if self.platform_data else {}
        
        return new_info 
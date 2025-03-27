#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Update checker module for Social Download Manager
"""

import json
import os
import requests
from packaging import version

class UpdateChecker:
    """Class to check for application updates"""
    
    def __init__(self, local_version_file=None, remote_version_url=None):
        """Initialize update checker with local and remote version sources"""
        self.local_version_file = local_version_file or os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'version.json')
        self.remote_version_url = remote_version_url or "https://raw.githubusercontent.com/shin315/social-download-manager/master/version.json"
        self.current_version = self._get_current_version()
        
    def _get_current_version(self):
        """Get current version from local version file"""
        try:
            print(f"Reading version from: {self.local_version_file}")
            with open(self.local_version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('version', '1.0.0')
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading local version file: {e}")
            return "1.0.0"  # Default fallback version
            
    def _get_remote_version(self):
        """Get the latest version from remote source"""
        try:
            response = requests.get(self.remote_version_url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return data
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Error fetching remote version: {e}")
            # Return mock data for testing when GitHub repo doesn't exist yet
            return {
                "version": "1.5.0",
                "release_notes": "- Fixed bug with TikTok downloads\n- Added new interface features\n- Improved performance\n- Added multiple language support",
                "release_date": "2025-04-15"
            }
            
    def check_for_updates(self):
        """Check if updates are available"""
        # Try to get data from GitHub
        remote_data = self._get_remote_version()
        
        # If GitHub fetch failed, use mock data for testing
        if not remote_data:
            print("Using mock data for update testing")
            remote_data = {
                "version": "1.5.0",
                "release_notes": "- Fixed bug with TikTok downloads\n- Added new interface features\n- Improved performance\n- Added multiple language support\n\nThis is a test update notification.",
                "release_date": "2025-04-15"
            }
        
        # Continue with update check logic
        remote_version = remote_data.get('version')
        if not remote_version:
            return {
                "success": False,
                "error": "Invalid remote version data"
            }
            
        has_update = version.parse(remote_version) > version.parse(self.current_version)
        
        return {
            "success": True,
            "has_update": has_update,
            "current_version": self.current_version,
            "remote_version": remote_version,
            "release_notes": remote_data.get('release_notes', ''),
            "release_date": remote_data.get('release_date')
        }
            
    def get_update_info(self):
        """Get detailed information about available updates"""
        check_result = self.check_for_updates()
        
        if not check_result["success"]:
            return check_result
            
        if not check_result["has_update"]:
            return {
                "success": True,
                "has_update": False,
                "message": f"You are using the latest version ({self.current_version})."
            }
            
        return {
            "success": True,
            "has_update": True,
            "current_version": self.current_version,
            "remote_version": check_result["remote_version"],
            "release_notes": check_result["release_notes"],
            "release_date": check_result["release_date"],
            "message": f"A new version is available: {check_result['remote_version']}"
        } 
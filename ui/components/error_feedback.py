"""
UI Components for Error Feedback Display

This module provides UI components for displaying user-friendly error messages
with different presentation styles (modal, toast, inline, banner).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any
import webbrowser
from datetime import datetime, timedelta

from core.user_feedback import (
    UserMessage, MessageType, UserRole, MessageDetailLevel,
    generate_user_friendly_message, get_error_recovery_suggestions
)
from data.models.error_management import ErrorInfo


class ErrorMessageDialog:
    """Modal dialog for displaying error messages"""
    
    def __init__(self, parent: tk.Widget, user_message: UserMessage):
        self.parent = parent
        self.user_message = user_message
        self.dialog = None
        self.result = None
        
    def show(self) -> str:
        """Show the error dialog and return user action"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.user_message.title or "Error")
        self.dialog.geometry("500x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        self._create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with icon and title
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Severity icon
        if self.user_message.severity_icon:
            icon_label = ttk.Label(header_frame, text=self.user_message.severity_icon, font=("Arial", 24))
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Title
        title_label = ttk.Label(
            header_frame, 
            text=self.user_message.title,
            font=("Arial", 14, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # Error code (if available)
        if self.user_message.error_code:
            code_label = ttk.Label(
                header_frame,
                text=f"({self.user_message.error_code})",
                font=("Arial", 10),
                foreground="gray"
            )
            code_label.pack(side=tk.RIGHT)
        
        # Message content
        message_frame = ttk.Frame(main_frame)
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Main message
        message_text = tk.Text(
            message_frame,
            wrap=tk.WORD,
            height=6,
            font=("Arial", 11),
            relief=tk.FLAT,
            background=self.dialog.cget("bg"),
            state=tk.DISABLED
        )
        message_text.pack(fill=tk.BOTH, expand=True)
        
        # Insert message content
        message_text.config(state=tk.NORMAL)
        message_text.insert(tk.END, self.user_message.message)
        message_text.config(state=tk.DISABLED)
        
        # Technical details (expandable)
        if self.user_message.technical_details:
            self._create_technical_details_section(main_frame)
        
        # Action buttons
        self._create_action_buttons(main_frame)
    
    def _create_technical_details_section(self, parent):
        """Create expandable technical details section"""
        details_frame = ttk.LabelFrame(parent, text="Technical Details", padding="10")
        details_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Technical details text
        details_text = tk.Text(
            details_frame,
            wrap=tk.WORD,
            height=4,
            font=("Courier", 9),
            relief=tk.SUNKEN,
            background="#f5f5f5"
        )
        details_text.pack(fill=tk.X)
        
        details_text.insert(tk.END, self.user_message.technical_details)
        details_text.config(state=tk.DISABLED)
    
    def _create_action_buttons(self, parent):
        """Create action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        # Retry button (if available)
        if self.user_message.retry_available:
            retry_btn = ttk.Button(
                button_frame,
                text="Retry",
                command=lambda: self._close_with_result("retry")
            )
            retry_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Help button (if help URL available)
        if self.user_message.help_url:
            help_btn = ttk.Button(
                button_frame,
                text="Get Help",
                command=self._open_help
            )
            help_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Contact support button (if needed)
        if self.user_message.contact_support:
            support_btn = ttk.Button(
                button_frame,
                text="Contact Support",
                command=lambda: self._close_with_result("contact_support")
            )
            support_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=lambda: self._close_with_result("close")
        )
        close_btn.pack(side=tk.RIGHT)
    
    def _open_help(self):
        """Open help URL in browser"""
        if self.user_message.help_url:
            webbrowser.open(self.user_message.help_url)
    
    def _close_with_result(self, result: str):
        """Close dialog with result"""
        self.result = result
        self.dialog.destroy()


class ErrorToastNotification:
    """Toast notification for non-blocking error messages"""
    
    def __init__(self, parent: tk.Widget, user_message: UserMessage, duration: int = 5000):
        self.parent = parent
        self.user_message = user_message
        self.duration = duration
        self.toast = None
        
    def show(self):
        """Show toast notification"""
        self.toast = tk.Toplevel(self.parent)
        self.toast.title("")
        self.toast.overrideredirect(True)  # Remove window decorations
        self.toast.attributes("-topmost", True)
        
        # Position at bottom right of screen
        self.toast.update_idletasks()
        width = 350
        height = 100
        screen_width = self.toast.winfo_screenwidth()
        screen_height = self.toast.winfo_screenheight()
        x = screen_width - width - 20
        y = screen_height - height - 60
        self.toast.geometry(f"{width}x{height}+{x}+{y}")
        
        self._create_toast_content()
        
        # Auto-hide after duration
        self.toast.after(self.duration, self._hide_toast)
    
    def _create_toast_content(self):
        """Create toast content"""
        # Main frame with background color based on severity
        bg_color = self.user_message.severity_color or "#f0f0f0"
        main_frame = tk.Frame(self.toast, bg=bg_color, relief=tk.RAISED, bd=2)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Content frame
        content_frame = tk.Frame(main_frame, bg=bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Icon and title
        header_frame = tk.Frame(content_frame, bg=bg_color)
        header_frame.pack(fill=tk.X)
        
        if self.user_message.severity_icon:
            icon_label = tk.Label(
                header_frame,
                text=self.user_message.severity_icon,
                bg=bg_color,
                font=("Arial", 16)
            )
            icon_label.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header_frame,
            text=self.user_message.title,
            bg=bg_color,
            font=("Arial", 10, "bold"),
            fg="white" if bg_color in ["#F44336", "#D32F2F"] else "black"
        )
        title_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Close button
        close_btn = tk.Button(
            header_frame,
            text="×",
            bg=bg_color,
            relief=tk.FLAT,
            font=("Arial", 12, "bold"),
            command=self._hide_toast,
            fg="white" if bg_color in ["#F44336", "#D32F2F"] else "black"
        )
        close_btn.pack(side=tk.RIGHT)
        
        # Message
        message_label = tk.Label(
            content_frame,
            text=self.user_message.message,
            bg=bg_color,
            font=("Arial", 9),
            wraplength=320,
            justify=tk.LEFT,
            fg="white" if bg_color in ["#F44336", "#D32F2F"] else "black"
        )
        message_label.pack(fill=tk.X, pady=(5, 0))
    
    def _hide_toast(self):
        """Hide toast notification"""
        if self.toast:
            self.toast.destroy()


class InlineErrorDisplay:
    """Inline error display for form validation"""
    
    def __init__(self, parent: tk.Widget, user_message: UserMessage):
        self.parent = parent
        self.user_message = user_message
        self.error_frame = None
        
    def show(self):
        """Show inline error message"""
        if self.error_frame:
            self.hide()
        
        self.error_frame = ttk.Frame(self.parent)
        self.error_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Error icon and message
        content_frame = ttk.Frame(self.error_frame)
        content_frame.pack(fill=tk.X)
        
        if self.user_message.severity_icon:
            icon_label = ttk.Label(
                content_frame,
                text=self.user_message.severity_icon,
                font=("Arial", 12)
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 5))
        
        message_label = ttk.Label(
            content_frame,
            text=self.user_message.message,
            font=("Arial", 9),
            foreground="red" if self.user_message.severity_color == "#F44336" else "orange"
        )
        message_label.pack(side=tk.LEFT)
        
        # Action text (if available)
        if self.user_message.action_text:
            action_label = ttk.Label(
                content_frame,
                text=f" {self.user_message.action_text}",
                font=("Arial", 9),
                foreground="blue"
            )
            action_label.pack(side=tk.LEFT)
    
    def hide(self):
        """Hide inline error message"""
        if self.error_frame:
            self.error_frame.destroy()
            self.error_frame = None


class ErrorBanner:
    """Banner for system-wide error messages"""
    
    def __init__(self, parent: tk.Widget, user_message: UserMessage):
        self.parent = parent
        self.user_message = user_message
        self.banner_frame = None
        
    def show(self):
        """Show error banner"""
        if self.banner_frame:
            self.hide()
        
        # Create banner at top of parent
        self.banner_frame = tk.Frame(
            self.parent,
            bg=self.user_message.severity_color or "#FF9800",
            height=60
        )
        self.banner_frame.pack(fill=tk.X, side=tk.TOP)
        self.banner_frame.pack_propagate(False)
        
        # Content frame
        content_frame = tk.Frame(self.banner_frame, bg=self.banner_frame.cget("bg"))
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Icon and message
        if self.user_message.severity_icon:
            icon_label = tk.Label(
                content_frame,
                text=self.user_message.severity_icon,
                bg=self.banner_frame.cget("bg"),
                font=("Arial", 16),
                fg="white"
            )
            icon_label.pack(side=tk.LEFT, padx=(0, 10))
        
        message_label = tk.Label(
            content_frame,
            text=f"{self.user_message.title}: {self.user_message.message}",
            bg=self.banner_frame.cget("bg"),
            font=("Arial", 11, "bold"),
            fg="white",
            wraplength=600
        )
        message_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Close button
        close_btn = tk.Button(
            content_frame,
            text="×",
            bg=self.banner_frame.cget("bg"),
            relief=tk.FLAT,
            font=("Arial", 14, "bold"),
            fg="white",
            command=self.hide
        )
        close_btn.pack(side=tk.RIGHT)
    
    def hide(self):
        """Hide error banner"""
        if self.banner_frame:
            self.banner_frame.destroy()
            self.banner_frame = None


class ErrorFeedbackManager:
    """Manager for displaying error feedback in UI"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.active_displays = {}
        
    def show_error(
        self,
        error_info: ErrorInfo,
        message_type: MessageType = MessageType.MODAL,
        user_role: UserRole = UserRole.END_USER,
        detail_level: MessageDetailLevel = MessageDetailLevel.STANDARD,
        callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Show error message with specified presentation type"""
        
        # Generate user-friendly message
        user_message = generate_user_friendly_message(
            error_info, user_role, detail_level, message_type
        )
        
        # Display based on message type
        if message_type == MessageType.MODAL:
            dialog = ErrorMessageDialog(self.parent, user_message)
            result = dialog.show()
            if callback:
                callback(result)
            return result
            
        elif message_type == MessageType.TOAST:
            toast = ErrorToastNotification(self.parent, user_message)
            toast.show()
            self.active_displays[f"toast_{error_info.error_id}"] = toast
            
        elif message_type == MessageType.INLINE:
            inline = InlineErrorDisplay(self.parent, user_message)
            inline.show()
            self.active_displays[f"inline_{error_info.error_id}"] = inline
            
        elif message_type == MessageType.BANNER:
            banner = ErrorBanner(self.parent, user_message)
            banner.show()
            self.active_displays[f"banner_{error_info.error_id}"] = banner
        
        return None
    
    def hide_error(self, error_id: str, message_type: MessageType):
        """Hide specific error display"""
        key = f"{message_type.value}_{error_id}"
        if key in self.active_displays:
            display = self.active_displays[key]
            if hasattr(display, 'hide'):
                display.hide()
            del self.active_displays[key]
    
    def hide_all_errors(self):
        """Hide all active error displays"""
        for display in self.active_displays.values():
            if hasattr(display, 'hide'):
                display.hide()
        self.active_displays.clear()
    
    def show_recovery_suggestions(self, error_info: ErrorInfo):
        """Show recovery suggestions dialog"""
        suggestions = get_error_recovery_suggestions(error_info)
        
        if not suggestions:
            return
        
        # Create suggestions dialog
        dialog = tk.Toplevel(self.parent)
        dialog.title("Recovery Suggestions")
        dialog.geometry("400x300")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (300 // 2)
        dialog.geometry(f"400x300+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Here are some things you can try:",
            font=("Arial", 12, "bold")
        )
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # Suggestions list
        for i, suggestion in enumerate(suggestions, 1):
            suggestion_frame = ttk.Frame(main_frame)
            suggestion_frame.pack(fill=tk.X, pady=(0, 10))
            
            number_label = ttk.Label(
                suggestion_frame,
                text=f"{i}.",
                font=("Arial", 10, "bold")
            )
            number_label.pack(side=tk.LEFT, anchor=tk.NW, padx=(0, 10))
            
            text_label = ttk.Label(
                suggestion_frame,
                text=suggestion,
                font=("Arial", 10),
                wraplength=320,
                justify=tk.LEFT
            )
            text_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Close button
        close_btn = ttk.Button(
            main_frame,
            text="Close",
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT, pady=(20, 0))


# Convenience functions for easy integration
def show_error_dialog(parent: tk.Widget, error_info: ErrorInfo, user_role: UserRole = UserRole.END_USER) -> str:
    """Show error dialog and return user action"""
    manager = ErrorFeedbackManager(parent)
    return manager.show_error(error_info, MessageType.MODAL, user_role)


def show_error_toast(parent: tk.Widget, error_info: ErrorInfo):
    """Show error toast notification"""
    manager = ErrorFeedbackManager(parent)
    manager.show_error(error_info, MessageType.TOAST)


def show_inline_error(parent: tk.Widget, error_info: ErrorInfo):
    """Show inline error message"""
    manager = ErrorFeedbackManager(parent)
    manager.show_error(error_info, MessageType.INLINE)


def show_error_banner(parent: tk.Widget, error_info: ErrorInfo):
    """Show error banner"""
    manager = ErrorFeedbackManager(parent)
    manager.show_error(error_info, MessageType.BANNER) 
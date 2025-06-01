"""
Card Component Styling

Enhanced styling system for card-based layouts that integrates with design tokens
and provides theme-aware visual hierarchy, shadows, and modern aesthetics.
"""

from typing import Dict, Optional
from .style_manager import StyleManager
from ..components.cards import ElevationLevel


class CardStyler:
    """
    Specialized styling system for card components
    
    Provides:
    - Design token integration for consistent styling
    - Theme-aware card appearance
    - Elevation-based shadow systems
    - Content hierarchy styling within cards
    """
    
    def __init__(self, style_manager: Optional[StyleManager] = None):
        """Initialize card styler with design system integration"""
        self.style_manager = style_manager or StyleManager()
    
    def get_card_base_styles(self) -> str:
        """
        Generate base card styling using design tokens
        
        Returns comprehensive CSS for all card components
        """
        # Get design token values
        bg_primary = self.style_manager.get_token_value('color-background-primary', '#FFFFFF')
        bg_secondary = self.style_manager.get_token_value('color-background-secondary', '#F8FAFC')
        border_color = self.style_manager.get_token_value('color-border-default', '#E2E8F0')
        border_radius = self.style_manager.get_token_value('sizing-border-radius-md', '8px')
        border_radius_lg = self.style_manager.get_token_value('sizing-border-radius-lg', '12px')
        
        # Text colors
        text_primary = self.style_manager.get_token_value('color-text-primary', '#0F172A')
        text_secondary = self.style_manager.get_token_value('color-text-secondary', '#475569')
        text_tertiary = self.style_manager.get_token_value('color-text-tertiary', '#94A3B8')
        
        # Typography tokens
        heading_size = self.style_manager.get_token_value('typography-heading-h4-size', '18px')
        heading_weight = self.style_manager.get_token_value('typography-heading-weight', '600')
        body_size = self.style_manager.get_token_value('typography-body-size', '14px')
        small_size = self.style_manager.get_token_value('typography-small-size', '12px')
        
        # Spacing tokens
        spacing_sm = self.style_manager.get_token_value('spacing-sm', '8px')
        spacing_md = self.style_manager.get_token_value('spacing-md', '16px')
        spacing_lg = self.style_manager.get_token_value('spacing-lg', '24px')
        
        return f"""
        /* Card Base Styles */
        CardComponent {{
            background-color: {bg_primary};
            border: 1px solid {border_color};
            border-radius: {border_radius};
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        CardComponent[clickable="true"] {{
            cursor: pointer;
        }}
        
        CardComponent[clickable="true"]:hover {{
            transform: translateY(-1px);
        }}
        
        /* Card Content Hierarchy */
        #card_title {{
            color: {text_primary};
            font-size: {heading_size};
            font-weight: {heading_weight};
            padding: {spacing_md} {spacing_md} {spacing_sm} {spacing_md};
            background-color: transparent;
            border: none;
            margin: 0px;
        }}
        
        #card_content {{
            background-color: transparent;
            border: none;
        }}
        
        /* Content Labels within Cards */
        CardComponent QLabel {{
            color: {text_secondary};
            font-size: {body_size};
            line-height: 1.5;
        }}
        
        CardComponent #video_title {{
            color: {text_primary};
            font-weight: 500;
            font-size: 16px;
            margin-bottom: {spacing_sm};
        }}
        
        CardComponent #video_url {{
            color: {text_tertiary};
            font-size: {small_size};
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        
        CardComponent #video_duration {{
            color: {text_secondary};
            font-size: {small_size};
            font-weight: 500;
        }}
        
        CardComponent #download_filename {{
            color: {text_primary};
            font-weight: 500;
            font-size: 15px;
        }}
        
        CardComponent #settings_title {{
            color: {text_primary};
            font-weight: 500;
            font-size: 16px;
            margin-bottom: {spacing_sm};
        }}
        
        CardComponent #settings_description {{
            color: {text_secondary};
            font-size: {body_size};
            line-height: 1.4;
        }}
        
        /* Container Styles */
        CardContainer {{
            background-color: {bg_secondary};
            border: none;
        }}
        
        CardContainer QScrollBar:vertical {{
            background-color: transparent;
            width: 8px;
            border-radius: 4px;
        }}
        
        CardContainer QScrollBar::handle:vertical {{
            background-color: rgba(0, 0, 0, 0.15);
            border-radius: 4px;
            min-height: 20px;
        }}
        
        CardContainer QScrollBar::handle:vertical:hover {{
            background-color: rgba(0, 0, 0, 0.25);
        }}
        
        CardContainer QScrollBar::handle:vertical:pressed {{
            background-color: rgba(0, 0, 0, 0.35);
        }}
        """
    
    def get_elevation_styles(self, elevation: ElevationLevel) -> str:
        """
        Generate elevation-specific shadow styles
        
        Args:
            elevation: Card elevation level
            
        Returns:
            CSS shadow styles for the specified elevation
        """
        elevation_shadows = {
            ElevationLevel.FLAT: "",
            ElevationLevel.SUBTLE: """
                box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.05),
                           0px 1px 2px rgba(0, 0, 0, 0.1);
            """,
            ElevationLevel.RAISED: """
                box-shadow: 0px 2px 4px rgba(0, 0, 0, 0.1),
                           0px 1px 2px rgba(0, 0, 0, 0.06);
            """,
            ElevationLevel.ELEVATED: """
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.12),
                           0px 2px 4px rgba(0, 0, 0, 0.08);
            """,
            ElevationLevel.FLOATING: """
                box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.15),
                           0px 4px 8px rgba(0, 0, 0, 0.10),
                           0px 2px 4px rgba(0, 0, 0, 0.06);
            """
        }
        
        return elevation_shadows.get(elevation, elevation_shadows[ElevationLevel.RAISED])
    
    def get_card_variant_styles(self, variant: str = "default") -> str:
        """
        Generate styles for different card variants
        
        Args:
            variant: Card variant ("default", "accent", "success", "warning", "error")
            
        Returns:
            CSS styles for the specified variant
        """
        # Get status colors from design tokens
        success_color = self.style_manager.get_token_value('color-status-success', '#10B981')
        warning_color = self.style_manager.get_token_value('color-status-warning', '#F59E0B')
        error_color = self.style_manager.get_token_value('color-status-error', '#EF4444')
        brand_color = self.style_manager.get_token_value('color-brand-primary-500', '#3B82F6')
        
        variant_styles = {
            "default": "",
            "accent": f"""
                border-left: 4px solid {brand_color};
            """,
            "success": f"""
                border-left: 4px solid {success_color};
            """,
            "warning": f"""
                border-left: 4px solid {warning_color};
            """,
            "error": f"""
                border-left: 4px solid {error_color};
            """
        }
        
        return variant_styles.get(variant, variant_styles["default"])
    
    def get_interactive_card_styles(self) -> str:
        """
        Generate styles for interactive (clickable/hoverable) cards
        
        Returns:
            CSS for enhanced interactive states
        """
        # Get hover colors
        bg_hover = self.style_manager.get_token_value('color-background-tertiary', '#F1F5F9')
        border_focus = self.style_manager.get_token_value('color-border-focus', '#3B82F6')
        
        return f"""
        CardComponent[clickable="true"]:hover {{
            background-color: {bg_hover};
            transform: translateY(-1px);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        CardComponent[clickable="true"]:active {{
            transform: translateY(0px);
            transition: all 0.1s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        CardComponent[clickable="true"]:focus {{
            outline: 2px solid {border_focus};
            outline-offset: 2px;
        }}
        """
    
    def get_responsive_card_styles(self) -> str:
        """
        Generate responsive styles for cards across different screen sizes
        
        Returns:
            CSS media queries for responsive card behavior
        """
        # Note: PyQt6 doesn't support CSS media queries, but we can provide
        # different style sets that can be applied programmatically
        
        # Mobile-friendly card styles (to be applied programmatically)
        return f"""
        /* Mobile Card Adaptations */
        CardComponent.mobile {{
            margin: 8px 4px;
            border-radius: 6px;
        }}
        
        CardComponent.mobile #card_title {{
            font-size: 16px;
            padding: 12px 12px 6px 12px;
        }}
        
        CardComponent.mobile #card_content {{
            padding: 12px;
        }}
        
        /* Tablet Card Adaptations */
        CardComponent.tablet {{
            margin: 12px 8px;
        }}
        
        /* Desktop Card Adaptations */
        CardComponent.desktop {{
            margin: 16px 12px;
        }}
        """
    
    def get_complete_card_stylesheet(self, 
                                   elevation: ElevationLevel = ElevationLevel.RAISED,
                                   variant: str = "default",
                                   interactive: bool = False) -> str:
        """
        Generate complete stylesheet for cards with all features
        
        Args:
            elevation: Default elevation level
            variant: Card variant style
            interactive: Whether to include interactive styles
            
        Returns:
            Complete CSS stylesheet for cards
        """
        styles = []
        
        # Base styles
        styles.append(self.get_card_base_styles())
        
        # Elevation styles
        elevation_css = self.get_elevation_styles(elevation)
        if elevation_css:
            styles.append(f"CardComponent {{ {elevation_css} }}")
        
        # Variant styles
        variant_css = self.get_card_variant_styles(variant)
        if variant_css:
            styles.append(f"CardComponent {{ {variant_css} }}")
        
        # Interactive styles
        if interactive:
            styles.append(self.get_interactive_card_styles())
        
        # Responsive styles
        styles.append(self.get_responsive_card_styles())
        
        return "\n\n".join(styles)


def create_themed_card_styles(theme_name: str) -> str:
    """
    Create complete card styles for a specific theme
    
    Args:
        theme_name: Name of the theme ('light', 'dark', etc.)
        
    Returns:
        Complete themed card stylesheet
    """
    style_manager = StyleManager()
    style_manager.switch_theme(theme_name)
    
    card_styler = CardStyler(style_manager)
    
    return card_styler.get_complete_card_stylesheet(
        elevation=ElevationLevel.RAISED,
        variant="default",
        interactive=True
    ) 
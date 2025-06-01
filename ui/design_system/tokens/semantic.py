"""
Semantic Design Tokens

Semantic tokens that reference primitive tokens and provide meaningful context
for UI components. These create the bridge between raw values and component usage.
"""

from typing import Dict, Any
from .base import TokenType, TokenMetadata, TokenReference
from .color import ColorToken
from .spacing import SpacingToken
from .typography import TypographyToken
from .sizing import SizingToken


class SemanticTokens:
    """Factory for creating semantic design tokens"""
    
    @staticmethod
    def create_ui_color_tokens() -> Dict[str, ColorToken]:
        """
        Create semantic UI color tokens that reference primitive colors
        
        These provide meaningful names for UI purposes (background, text, border, etc.)
        """
        tokens = {}
        
        # === BACKGROUND COLORS ===
        tokens['color-background-primary'] = ColorToken(
            'color-background-primary',
            TokenReference('color-neutral-white'),
            TokenMetadata(
                description="Primary background color for main content areas",
                token_type=TokenType.SEMANTIC,
                tags={'background', 'primary', 'semantic'}
            )
        )
        
        tokens['color-background-secondary'] = ColorToken(
            'color-background-secondary',
            TokenReference('color-neutral-50'),
            TokenMetadata(
                description="Secondary background for cards, panels, modals",
                token_type=TokenType.SEMANTIC,
                tags={'background', 'secondary', 'semantic'}
            )
        )
        
        tokens['color-background-tertiary'] = ColorToken(
            'color-background-tertiary',
            TokenReference('color-neutral-100'),
            TokenMetadata(
                description="Tertiary background for subtle sections",
                token_type=TokenType.SEMANTIC,
                tags={'background', 'tertiary', 'semantic'}
            )
        )
        
        tokens['color-background-inverse'] = ColorToken(
            'color-background-inverse',
            TokenReference('color-neutral-900'),
            TokenMetadata(
                description="Inverse background for dark surfaces",
                token_type=TokenType.SEMANTIC,
                tags={'background', 'inverse', 'dark', 'semantic'}
            )
        )
        
        # === TEXT COLORS ===
        tokens['color-text-primary'] = ColorToken(
            'color-text-primary',
            TokenReference('color-neutral-900'),
            TokenMetadata(
                description="Primary text color for headings and important content",
                token_type=TokenType.SEMANTIC,
                tags={'text', 'primary', 'semantic'}
            )
        )
        
        tokens['color-text-secondary'] = ColorToken(
            'color-text-secondary',
            TokenReference('color-neutral-600'),
            TokenMetadata(
                description="Secondary text color for body text and descriptions",
                token_type=TokenType.SEMANTIC,
                tags={'text', 'secondary', 'semantic'}
            )
        )
        
        tokens['color-text-tertiary'] = ColorToken(
            'color-text-tertiary',
            TokenReference('color-neutral-400'),
            TokenMetadata(
                description="Tertiary text color for subtle labels and placeholders",
                token_type=TokenType.SEMANTIC,
                tags={'text', 'tertiary', 'semantic'}
            )
        )
        
        tokens['color-text-inverse'] = ColorToken(
            'color-text-inverse',
            TokenReference('color-neutral-white'),
            TokenMetadata(
                description="Inverse text color for dark backgrounds",
                token_type=TokenType.SEMANTIC,
                tags={'text', 'inverse', 'semantic'}
            )
        )
        
        tokens['color-text-link'] = ColorToken(
            'color-text-link',
            TokenReference('color-brand-primary-600'),
            TokenMetadata(
                description="Link text color",
                token_type=TokenType.SEMANTIC,
                tags={'text', 'link', 'interactive', 'semantic'}
            )
        )
        
        tokens['color-text-link-hover'] = ColorToken(
            'color-text-link-hover',
            TokenReference('color-brand-primary-700'),
            TokenMetadata(
                description="Link text color on hover",
                token_type=TokenType.SEMANTIC,
                tags={'text', 'link', 'hover', 'interactive', 'semantic'}
            )
        )
        
        # === BORDER COLORS ===
        tokens['color-border-default'] = ColorToken(
            'color-border-default',
            TokenReference('color-neutral-200'),
            TokenMetadata(
                description="Default border color for components",
                token_type=TokenType.SEMANTIC,
                tags={'border', 'default', 'semantic'}
            )
        )
        
        tokens['color-border-strong'] = ColorToken(
            'color-border-strong',
            TokenReference('color-neutral-300'),
            TokenMetadata(
                description="Strong border color for emphasis",
                token_type=TokenType.SEMANTIC,
                tags={'border', 'strong', 'semantic'}
            )
        )
        
        tokens['color-border-focus'] = ColorToken(
            'color-border-focus',
            TokenReference('color-brand-primary-500'),
            TokenMetadata(
                description="Border color for focused elements",
                token_type=TokenType.SEMANTIC,
                tags={'border', 'focus', 'interactive', 'semantic'}
            )
        )
        
        # === BUTTON COLORS ===
        tokens['color-button-primary-background'] = ColorToken(
            'color-button-primary-background',
            TokenReference('color-brand-primary-500'),
            TokenMetadata(
                description="Primary button background color",
                token_type=TokenType.SEMANTIC,
                tags={'button', 'primary', 'background', 'semantic'}
            )
        )
        
        tokens['color-button-primary-background-hover'] = ColorToken(
            'color-button-primary-background-hover',
            TokenReference('color-brand-primary-600'),
            TokenMetadata(
                description="Primary button background color on hover",
                token_type=TokenType.SEMANTIC,
                tags={'button', 'primary', 'background', 'hover', 'semantic'}
            )
        )
        
        tokens['color-button-primary-text'] = ColorToken(
            'color-button-primary-text',
            TokenReference('color-neutral-white'),
            TokenMetadata(
                description="Primary button text color",
                token_type=TokenType.SEMANTIC,
                tags={'button', 'primary', 'text', 'semantic'}
            )
        )
        
        tokens['color-button-secondary-background'] = ColorToken(
            'color-button-secondary-background',
            TokenReference('color-neutral-100'),
            TokenMetadata(
                description="Secondary button background color",
                token_type=TokenType.SEMANTIC,
                tags={'button', 'secondary', 'background', 'semantic'}
            )
        )
        
        tokens['color-button-secondary-text'] = ColorToken(
            'color-button-secondary-text',
            TokenReference('color-neutral-700'),
            TokenMetadata(
                description="Secondary button text color",
                token_type=TokenType.SEMANTIC,
                tags={'button', 'secondary', 'text', 'semantic'}
            )
        )
        
        # === STATUS COLORS ===
        tokens['color-status-success'] = ColorToken(
            'color-status-success',
            TokenReference('color-semantic-success-500'),
            TokenMetadata(
                description="Success status color",
                token_type=TokenType.SEMANTIC,
                tags={'status', 'success', 'semantic'}
            )
        )
        
        tokens['color-status-warning'] = ColorToken(
            'color-status-warning',
            TokenReference('color-semantic-warning-500'),
            TokenMetadata(
                description="Warning status color",
                token_type=TokenType.SEMANTIC,
                tags={'status', 'warning', 'semantic'}
            )
        )
        
        tokens['color-status-error'] = ColorToken(
            'color-status-error',
            TokenReference('color-semantic-error-500'),
            TokenMetadata(
                description="Error status color",
                token_type=TokenType.SEMANTIC,
                tags={'status', 'error', 'semantic'}
            )
        )
        
        tokens['color-status-info'] = ColorToken(
            'color-status-info',
            TokenReference('color-semantic-info-500'),
            TokenMetadata(
                description="Info status color",
                token_type=TokenType.SEMANTIC,
                tags={'status', 'info', 'semantic'}
            )
        )
        
        return tokens
    
    @staticmethod
    def create_layout_spacing_tokens() -> Dict[str, SpacingToken]:
        """
        Create semantic spacing tokens for layout and components
        
        These provide meaningful names for spacing purposes
        """
        tokens = {}
        
        # === COMPONENT SPACING ===
        tokens['spacing-component-padding-xs'] = SpacingToken(
            'spacing-component-padding-xs',
            TokenReference('spacing-1'),  # 4px
            TokenMetadata(
                description="Extra small component padding",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'padding', 'component', 'xs', 'semantic'}
            )
        )
        
        tokens['spacing-component-padding-sm'] = SpacingToken(
            'spacing-component-padding-sm',
            TokenReference('spacing-2'),  # 8px
            TokenMetadata(
                description="Small component padding",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'padding', 'component', 'sm', 'semantic'}
            )
        )
        
        tokens['spacing-component-padding-md'] = SpacingToken(
            'spacing-component-padding-md',
            TokenReference('spacing-4'),  # 16px
            TokenMetadata(
                description="Medium component padding",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'padding', 'component', 'md', 'semantic'}
            )
        )
        
        tokens['spacing-component-padding-lg'] = SpacingToken(
            'spacing-component-padding-lg',
            TokenReference('spacing-6'),  # 24px
            TokenMetadata(
                description="Large component padding",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'padding', 'component', 'lg', 'semantic'}
            )
        )
        
        tokens['spacing-component-padding-xl'] = SpacingToken(
            'spacing-component-padding-xl',
            TokenReference('spacing-8'),  # 32px
            TokenMetadata(
                description="Extra large component padding",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'padding', 'component', 'xl', 'semantic'}
            )
        )
        
        # === LAYOUT GAPS ===
        tokens['spacing-layout-gap-xs'] = SpacingToken(
            'spacing-layout-gap-xs',
            TokenReference('spacing-2'),  # 8px
            TokenMetadata(
                description="Extra small layout gap between elements",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'gap', 'layout', 'xs', 'semantic'}
            )
        )
        
        tokens['spacing-layout-gap-sm'] = SpacingToken(
            'spacing-layout-gap-sm',
            TokenReference('spacing-3'),  # 12px
            TokenMetadata(
                description="Small layout gap between elements",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'gap', 'layout', 'sm', 'semantic'}
            )
        )
        
        tokens['spacing-layout-gap-md'] = SpacingToken(
            'spacing-layout-gap-md',
            TokenReference('spacing-4'),  # 16px
            TokenMetadata(
                description="Medium layout gap between elements",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'gap', 'layout', 'md', 'semantic'}
            )
        )
        
        tokens['spacing-layout-gap-lg'] = SpacingToken(
            'spacing-layout-gap-lg',
            TokenReference('spacing-6'),  # 24px
            TokenMetadata(
                description="Large layout gap between elements",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'gap', 'layout', 'lg', 'semantic'}
            )
        )
        
        tokens['spacing-layout-gap-xl'] = SpacingToken(
            'spacing-layout-gap-xl',
            TokenReference('spacing-8'),  # 32px
            TokenMetadata(
                description="Extra large layout gap between elements",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'gap', 'layout', 'xl', 'semantic'}
            )
        )
        
        # === SECTION SPACING ===
        tokens['spacing-section-margin-sm'] = SpacingToken(
            'spacing-section-margin-sm',
            TokenReference('spacing-8'),  # 32px
            TokenMetadata(
                description="Small section margin",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'margin', 'section', 'sm', 'semantic'}
            )
        )
        
        tokens['spacing-section-margin-md'] = SpacingToken(
            'spacing-section-margin-md',
            TokenReference('spacing-12'),  # 48px
            TokenMetadata(
                description="Medium section margin",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'margin', 'section', 'md', 'semantic'}
            )
        )
        
        tokens['spacing-section-margin-lg'] = SpacingToken(
            'spacing-section-margin-lg',
            TokenReference('spacing-16'),  # 64px
            TokenMetadata(
                description="Large section margin",
                token_type=TokenType.SEMANTIC,
                tags={'spacing', 'margin', 'section', 'lg', 'semantic'}
            )
        )
        
        return tokens
    
    @staticmethod
    def create_typography_tokens() -> Dict[str, TypographyToken]:
        """
        Create semantic typography tokens for UI components
        
        These provide meaningful names for typography usage
        """
        tokens = {}
        
        # === HEADING STYLES ===
        tokens['typography-heading-display'] = TypographyToken(
            'typography-heading-display',
            TokenReference('font-size-6xl'),  # 36pt
            TokenMetadata(
                description="Display heading - largest text for hero sections",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'heading', 'display', 'semantic'}
            )
        )
        
        tokens['typography-heading-h1'] = TypographyToken(
            'typography-heading-h1',
            TokenReference('font-size-5xl'),  # 30pt
            TokenMetadata(
                description="H1 heading - page titles",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'heading', 'h1', 'semantic'}
            )
        )
        
        tokens['typography-heading-h2'] = TypographyToken(
            'typography-heading-h2',
            TokenReference('font-size-4xl'),  # 24pt
            TokenMetadata(
                description="H2 heading - section titles",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'heading', 'h2', 'semantic'}
            )
        )
        
        tokens['typography-heading-h3'] = TypographyToken(
            'typography-heading-h3',
            TokenReference('font-size-3xl'),  # 20pt
            TokenMetadata(
                description="H3 heading - subsection titles",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'heading', 'h3', 'semantic'}
            )
        )
        
        tokens['typography-heading-h4'] = TypographyToken(
            'typography-heading-h4',
            TokenReference('font-size-2xl'),  # 18pt
            TokenMetadata(
                description="H4 heading - component titles",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'heading', 'h4', 'semantic'}
            )
        )
        
        # === BODY TEXT ===
        tokens['typography-body-large'] = TypographyToken(
            'typography-body-large',
            TokenReference('font-size-lg'),  # 14pt
            TokenMetadata(
                description="Large body text for important content",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'body', 'large', 'semantic'}
            )
        )
        
        tokens['typography-body-default'] = TypographyToken(
            'typography-body-default',
            TokenReference('font-size-base'),  # 12pt
            TokenMetadata(
                description="Default body text for general content",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'body', 'default', 'semantic'}
            )
        )
        
        tokens['typography-body-small'] = TypographyToken(
            'typography-body-small',
            TokenReference('font-size-sm'),  # 11pt
            TokenMetadata(
                description="Small body text for secondary content",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'body', 'small', 'semantic'}
            )
        )
        
        # === UI LABELS ===
        tokens['typography-label-default'] = TypographyToken(
            'typography-label-default',
            TokenReference('font-size-sm'),  # 11pt
            TokenMetadata(
                description="Default label text for form fields",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'label', 'default', 'semantic'}
            )
        )
        
        tokens['typography-label-small'] = TypographyToken(
            'typography-label-small',
            TokenReference('font-size-xs'),  # 10pt
            TokenMetadata(
                description="Small label text for compact interfaces",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'label', 'small', 'semantic'}
            )
        )
        
        # === BUTTON TEXT ===
        tokens['typography-button-default'] = TypographyToken(
            'typography-button-default',
            TokenReference('font-size-base'),  # 12pt
            TokenMetadata(
                description="Default button text size",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'button', 'default', 'semantic'}
            )
        )
        
        tokens['typography-button-small'] = TypographyToken(
            'typography-button-small',
            TokenReference('font-size-sm'),  # 11pt
            TokenMetadata(
                description="Small button text size",
                token_type=TokenType.SEMANTIC,
                tags={'typography', 'button', 'small', 'semantic'}
            )
        )
        
        return tokens
    
    @staticmethod
    def create_component_sizing_tokens() -> Dict[str, SizingToken]:
        """
        Create semantic sizing tokens for UI components
        
        These provide meaningful names for component dimensions
        """
        tokens = {}
        
        # === BUTTON SIZES ===
        tokens['size-button-height-sm'] = SizingToken(
            'size-button-height-sm',
            TokenReference('size-8'),  # 32px
            TokenMetadata(
                description="Small button height",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'button', 'height', 'sm', 'semantic'}
            )
        )
        
        tokens['size-button-height-md'] = SizingToken(
            'size-button-height-md',
            TokenReference('size-10'),  # 40px
            TokenMetadata(
                description="Medium button height",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'button', 'height', 'md', 'semantic'}
            )
        )
        
        tokens['size-button-height-lg'] = SizingToken(
            'size-button-height-lg',
            TokenReference('size-12'),  # 48px
            TokenMetadata(
                description="Large button height",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'button', 'height', 'lg', 'semantic'}
            )
        )
        
        # === INPUT SIZES ===
        tokens['size-input-height-sm'] = SizingToken(
            'size-input-height-sm',
            TokenReference('size-8'),  # 32px
            TokenMetadata(
                description="Small input field height",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'input', 'height', 'sm', 'semantic'}
            )
        )
        
        tokens['size-input-height-md'] = SizingToken(
            'size-input-height-md',
            TokenReference('size-10'),  # 40px
            TokenMetadata(
                description="Medium input field height",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'input', 'height', 'md', 'semantic'}
            )
        )
        
        tokens['size-input-height-lg'] = SizingToken(
            'size-input-height-lg',
            TokenReference('size-12'),  # 48px
            TokenMetadata(
                description="Large input field height",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'input', 'height', 'lg', 'semantic'}
            )
        )
        
        # === ICON SIZES ===
        tokens['size-icon-xs'] = SizingToken(
            'size-icon-xs',
            TokenReference('size-4'),  # 16px
            TokenMetadata(
                description="Extra small icon size",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'icon', 'xs', 'semantic'}
            )
        )
        
        tokens['size-icon-sm'] = SizingToken(
            'size-icon-sm',
            TokenReference('size-5'),  # 20px
            TokenMetadata(
                description="Small icon size",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'icon', 'sm', 'semantic'}
            )
        )
        
        tokens['size-icon-md'] = SizingToken(
            'size-icon-md',
            TokenReference('size-6'),  # 24px
            TokenMetadata(
                description="Medium icon size",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'icon', 'md', 'semantic'}
            )
        )
        
        tokens['size-icon-lg'] = SizingToken(
            'size-icon-lg',
            TokenReference('size-8'),  # 32px
            TokenMetadata(
                description="Large icon size",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'icon', 'lg', 'semantic'}
            )
        )
        
        # === CONTAINER WIDTHS ===
        tokens['size-container-sm'] = SizingToken(
            'size-container-sm',
            640,  # 640px
            TokenMetadata(
                description="Small container max width",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'container', 'width', 'sm', 'semantic'}
            )
        )
        
        tokens['size-container-md'] = SizingToken(
            'size-container-md',
            768,  # 768px
            TokenMetadata(
                description="Medium container max width",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'container', 'width', 'md', 'semantic'}
            )
        )
        
        tokens['size-container-lg'] = SizingToken(
            'size-container-lg',
            1024,  # 1024px
            TokenMetadata(
                description="Large container max width",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'container', 'width', 'lg', 'semantic'}
            )
        )
        
        tokens['size-container-xl'] = SizingToken(
            'size-container-xl',
            1280,  # 1280px
            TokenMetadata(
                description="Extra large container max width",
                token_type=TokenType.SEMANTIC,
                tags={'size', 'container', 'width', 'xl', 'semantic'}
            )
        )
        
        return tokens
    
    @classmethod
    def create_all_semantic_tokens(cls) -> Dict[str, Any]:
        """Create all semantic tokens"""
        all_tokens = {}
        
        all_tokens.update(cls.create_ui_color_tokens())
        all_tokens.update(cls.create_layout_spacing_tokens())
        all_tokens.update(cls.create_typography_tokens())
        all_tokens.update(cls.create_component_sizing_tokens())
        
        return all_tokens 
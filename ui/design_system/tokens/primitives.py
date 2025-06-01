"""
Primitive Design Tokens

Base primitive tokens that serve as the foundation for the entire design system.
These are the raw values that semantic tokens will reference.
"""

from typing import Dict, Any
from .base import TokenType, TokenMetadata
from .color import ColorToken
from .spacing import SpacingToken
from .typography import TypographyToken
from .sizing import SizingToken


class PrimitiveTokens:
    """Factory for creating primitive design tokens"""
    
    @staticmethod
    def create_color_palette() -> Dict[str, ColorToken]:
        """
        Create comprehensive color palette for Social Download Manager
        
        Includes:
        - Brand colors (primary, secondary)
        - Neutral scales for light/dark themes
        - Semantic colors (success, warning, error, info)
        - UI colors (borders, backgrounds, surfaces)
        """
        tokens = {}
        
        # === BRAND COLORS ===
        # Primary brand color - Modern blue for social media theme
        tokens['color-brand-primary-500'] = ColorToken(
            'color-brand-primary-500', 
            '#3B82F6',  # Modern blue
            TokenMetadata(
                description="Primary brand color - main blue",
                token_type=TokenType.PRIMITIVE,
                tags={'brand', 'primary', 'blue'}
            )
        )
        
        # Primary color scale
        tokens['color-brand-primary-50'] = ColorToken('color-brand-primary-50', '#EFF6FF', 
            TokenMetadata(description="Primary 50 - lightest blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-100'] = ColorToken('color-brand-primary-100', '#DBEAFE',
            TokenMetadata(description="Primary 100 - very light blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-200'] = ColorToken('color-brand-primary-200', '#BFDBFE',
            TokenMetadata(description="Primary 200 - light blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-300'] = ColorToken('color-brand-primary-300', '#93C5FD',
            TokenMetadata(description="Primary 300 - medium light blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-400'] = ColorToken('color-brand-primary-400', '#60A5FA',
            TokenMetadata(description="Primary 400 - medium blue", token_type=TokenType.PRIMITIVE))
        # 500 already defined above
        tokens['color-brand-primary-600'] = ColorToken('color-brand-primary-600', '#2563EB',
            TokenMetadata(description="Primary 600 - medium dark blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-700'] = ColorToken('color-brand-primary-700', '#1D4ED8',
            TokenMetadata(description="Primary 700 - dark blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-800'] = ColorToken('color-brand-primary-800', '#1E40AF',
            TokenMetadata(description="Primary 800 - very dark blue", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-primary-900'] = ColorToken('color-brand-primary-900', '#1E3A8A',
            TokenMetadata(description="Primary 900 - darkest blue", token_type=TokenType.PRIMITIVE))
        
        # Secondary brand color - Vibrant accent
        tokens['color-brand-secondary-500'] = ColorToken(
            'color-brand-secondary-500', 
            '#8B5CF6',  # Purple accent
            TokenMetadata(
                description="Secondary brand color - purple accent",
                token_type=TokenType.PRIMITIVE,
                tags={'brand', 'secondary', 'purple', 'accent'}
            )
        )
        
        # Secondary color scale
        tokens['color-brand-secondary-50'] = ColorToken('color-brand-secondary-50', '#F5F3FF',
            TokenMetadata(description="Secondary 50 - lightest purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-100'] = ColorToken('color-brand-secondary-100', '#EDE9FE',
            TokenMetadata(description="Secondary 100 - very light purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-200'] = ColorToken('color-brand-secondary-200', '#DDD6FE',
            TokenMetadata(description="Secondary 200 - light purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-300'] = ColorToken('color-brand-secondary-300', '#C4B5FD',
            TokenMetadata(description="Secondary 300 - medium light purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-400'] = ColorToken('color-brand-secondary-400', '#A78BFA',
            TokenMetadata(description="Secondary 400 - medium purple", token_type=TokenType.PRIMITIVE))
        # 500 already defined above
        tokens['color-brand-secondary-600'] = ColorToken('color-brand-secondary-600', '#7C3AED',
            TokenMetadata(description="Secondary 600 - medium dark purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-700'] = ColorToken('color-brand-secondary-700', '#6D28D9',
            TokenMetadata(description="Secondary 700 - dark purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-800'] = ColorToken('color-brand-secondary-800', '#5B21B6',
            TokenMetadata(description="Secondary 800 - very dark purple", token_type=TokenType.PRIMITIVE))
        tokens['color-brand-secondary-900'] = ColorToken('color-brand-secondary-900', '#4C1D95',
            TokenMetadata(description="Secondary 900 - darkest purple", token_type=TokenType.PRIMITIVE))
        
        # === NEUTRAL COLORS ===
        # Light theme neutrals (cool grays)
        tokens['color-neutral-white'] = ColorToken('color-neutral-white', '#FFFFFF',
            TokenMetadata(description="Pure white", token_type=TokenType.PRIMITIVE, tags={'neutral', 'light'}))
        tokens['color-neutral-50'] = ColorToken('color-neutral-50', '#F8FAFC',
            TokenMetadata(description="Neutral 50 - near white", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-100'] = ColorToken('color-neutral-100', '#F1F5F9',
            TokenMetadata(description="Neutral 100 - very light gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-200'] = ColorToken('color-neutral-200', '#E2E8F0',
            TokenMetadata(description="Neutral 200 - light gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-300'] = ColorToken('color-neutral-300', '#CBD5E1',
            TokenMetadata(description="Neutral 300 - medium light gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-400'] = ColorToken('color-neutral-400', '#94A3B8',
            TokenMetadata(description="Neutral 400 - medium gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-500'] = ColorToken('color-neutral-500', '#64748B',
            TokenMetadata(description="Neutral 500 - base gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-600'] = ColorToken('color-neutral-600', '#475569',
            TokenMetadata(description="Neutral 600 - medium dark gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-700'] = ColorToken('color-neutral-700', '#334155',
            TokenMetadata(description="Neutral 700 - dark gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-800'] = ColorToken('color-neutral-800', '#1E293B',
            TokenMetadata(description="Neutral 800 - very dark gray", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-900'] = ColorToken('color-neutral-900', '#0F172A',
            TokenMetadata(description="Neutral 900 - near black", token_type=TokenType.PRIMITIVE))
        tokens['color-neutral-black'] = ColorToken('color-neutral-black', '#000000',
            TokenMetadata(description="Pure black", token_type=TokenType.PRIMITIVE, tags={'neutral', 'dark'}))
        
        # === SEMANTIC COLORS ===
        # Success colors (green)
        tokens['color-semantic-success-500'] = ColorToken('color-semantic-success-500', '#10B981',
            TokenMetadata(description="Success color - emerald green", token_type=TokenType.PRIMITIVE, tags={'semantic', 'success'}))
        tokens['color-semantic-success-50'] = ColorToken('color-semantic-success-50', '#ECFDF5',
            TokenMetadata(description="Success background - very light green", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-success-100'] = ColorToken('color-semantic-success-100', '#D1FAE5',
            TokenMetadata(description="Success background - light green", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-success-600'] = ColorToken('color-semantic-success-600', '#059669',
            TokenMetadata(description="Success border/text - dark green", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-success-700'] = ColorToken('color-semantic-success-700', '#047857',
            TokenMetadata(description="Success hover - darker green", token_type=TokenType.PRIMITIVE))
        
        # Warning colors (amber)
        tokens['color-semantic-warning-500'] = ColorToken('color-semantic-warning-500', '#F59E0B',
            TokenMetadata(description="Warning color - amber", token_type=TokenType.PRIMITIVE, tags={'semantic', 'warning'}))
        tokens['color-semantic-warning-50'] = ColorToken('color-semantic-warning-50', '#FFFBEB',
            TokenMetadata(description="Warning background - very light amber", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-warning-100'] = ColorToken('color-semantic-warning-100', '#FEF3C7',
            TokenMetadata(description="Warning background - light amber", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-warning-600'] = ColorToken('color-semantic-warning-600', '#D97706',
            TokenMetadata(description="Warning border/text - dark amber", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-warning-700'] = ColorToken('color-semantic-warning-700', '#B45309',
            TokenMetadata(description="Warning hover - darker amber", token_type=TokenType.PRIMITIVE))
        
        # Error colors (red)
        tokens['color-semantic-error-500'] = ColorToken('color-semantic-error-500', '#EF4444',
            TokenMetadata(description="Error color - red", token_type=TokenType.PRIMITIVE, tags={'semantic', 'error'}))
        tokens['color-semantic-error-50'] = ColorToken('color-semantic-error-50', '#FEF2F2',
            TokenMetadata(description="Error background - very light red", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-error-100'] = ColorToken('color-semantic-error-100', '#FEE2E2',
            TokenMetadata(description="Error background - light red", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-error-600'] = ColorToken('color-semantic-error-600', '#DC2626',
            TokenMetadata(description="Error border/text - dark red", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-error-700'] = ColorToken('color-semantic-error-700', '#B91C1C',
            TokenMetadata(description="Error hover - darker red", token_type=TokenType.PRIMITIVE))
        
        # Info colors (blue)
        tokens['color-semantic-info-500'] = ColorToken('color-semantic-info-500', '#06B6D4',
            TokenMetadata(description="Info color - cyan", token_type=TokenType.PRIMITIVE, tags={'semantic', 'info'}))
        tokens['color-semantic-info-50'] = ColorToken('color-semantic-info-50', '#ECFEFF',
            TokenMetadata(description="Info background - very light cyan", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-info-100'] = ColorToken('color-semantic-info-100', '#CFFAFE',
            TokenMetadata(description="Info background - light cyan", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-info-600'] = ColorToken('color-semantic-info-600', '#0891B2',
            TokenMetadata(description="Info border/text - dark cyan", token_type=TokenType.PRIMITIVE))
        tokens['color-semantic-info-700'] = ColorToken('color-semantic-info-700', '#0E7490',
            TokenMetadata(description="Info hover - darker cyan", token_type=TokenType.PRIMITIVE))
        
        return tokens
    
    @staticmethod
    def create_spacing_scale() -> Dict[str, SpacingToken]:
        """
        Create spacing scale for Social Download Manager
        
        Follows 8px base grid system for consistent spacing
        """
        tokens = {}
        
        # Base spacing scale (8px grid)
        spacing_values = {
            'spacing-0': 0,
            'spacing-1': 4,    # 0.25rem
            'spacing-2': 8,    # 0.5rem - base unit
            'spacing-3': 12,   # 0.75rem
            'spacing-4': 16,   # 1rem
            'spacing-5': 20,   # 1.25rem
            'spacing-6': 24,   # 1.5rem
            'spacing-8': 32,   # 2rem
            'spacing-10': 40,  # 2.5rem
            'spacing-12': 48,  # 3rem
            'spacing-16': 64,  # 4rem
            'spacing-20': 80,  # 5rem
            'spacing-24': 96,  # 6rem
            'spacing-32': 128, # 8rem
            'spacing-40': 160, # 10rem
            'spacing-48': 192, # 12rem
            'spacing-56': 224, # 14rem
            'spacing-64': 256, # 16rem
        }
        
        for name, value in spacing_values.items():
            tokens[name] = SpacingToken(
                name, 
                value,
                TokenMetadata(
                    description=f"Spacing {value}px - {value/16}rem",
                    token_type=TokenType.PRIMITIVE,
                    tags={'spacing', 'primitive', '8px-grid'}
                )
            )
        
        return tokens
    
    @staticmethod
    def create_typography_scale() -> Dict[str, TypographyToken]:
        """
        Create typography scale for Social Download Manager
        
        Includes font sizes, weights, and font families
        """
        tokens = {}
        
        # Font families
        tokens['font-family-sans'] = TypographyToken(
            'font-family-sans',
            'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            TokenMetadata(
                description="Primary sans-serif font family",
                token_type=TokenType.PRIMITIVE,
                tags={'typography', 'font-family', 'sans-serif'}
            )
        )
        
        tokens['font-family-mono'] = TypographyToken(
            'font-family-mono',
            '"JetBrains Mono", "Fira Code", Monaco, Consolas, monospace',
            TokenMetadata(
                description="Monospace font family for code/technical content",
                token_type=TokenType.PRIMITIVE,
                tags={'typography', 'font-family', 'monospace'}
            )
        )
        
        # Font sizes (using pt for PyQt compatibility)
        font_sizes = {
            'font-size-xs': 10,    # Extra small
            'font-size-sm': 11,    # Small
            'font-size-base': 12,  # Base size
            'font-size-md': 13,    # Medium
            'font-size-lg': 14,    # Large
            'font-size-xl': 16,    # Extra large
            'font-size-2xl': 18,   # 2x large
            'font-size-3xl': 20,   # 3x large
            'font-size-4xl': 24,   # 4x large
            'font-size-5xl': 30,   # 5x large
            'font-size-6xl': 36,   # 6x large
        }
        
        for name, size in font_sizes.items():
            tokens[name] = TypographyToken(
                name,
                size,
                TokenMetadata(
                    description=f"Font size {size}pt",
                    token_type=TokenType.PRIMITIVE,
                    tags={'typography', 'font-size'}
                )
            )
        
        # Font weights
        font_weights = {
            'font-weight-light': 300,
            'font-weight-normal': 400,
            'font-weight-medium': 500,
            'font-weight-semibold': 600,
            'font-weight-bold': 700,
            'font-weight-extrabold': 800,
        }
        
        for name, weight in font_weights.items():
            tokens[name] = TypographyToken(
                name,
                weight,
                TokenMetadata(
                    description=f"Font weight {weight}",
                    token_type=TokenType.PRIMITIVE,
                    tags={'typography', 'font-weight'}
                )
            )
        
        return tokens
    
    @staticmethod
    def create_sizing_scale() -> Dict[str, SizingToken]:
        """
        Create sizing scale for Social Download Manager
        
        Includes dimensions for components and layouts
        """
        tokens = {}
        
        # Component sizing scale
        sizing_values = {
            'size-0': 0,
            'size-1': 4,
            'size-2': 8,
            'size-3': 12,
            'size-4': 16,
            'size-5': 20,
            'size-6': 24,
            'size-8': 32,
            'size-10': 40,
            'size-12': 48,
            'size-16': 64,
            'size-20': 80,
            'size-24': 96,
            'size-32': 128,
            'size-40': 160,
            'size-48': 192,
            'size-56': 224,
            'size-64': 256,
            'size-80': 320,
            'size-96': 384,
        }
        
        for name, value in sizing_values.items():
            tokens[name] = SizingToken(
                name,
                value,
                TokenMetadata(
                    description=f"Size {value}px",
                    token_type=TokenType.PRIMITIVE,
                    tags={'sizing', 'dimension'}
                )
            )
        
        # Special sizing values
        special_sizes = {
            'size-auto': 'auto',
            'size-full': '100%',
            'size-screen': '100vh',
            'size-min': 'min-content',
            'size-max': 'max-content',
        }
        
        for name, value in special_sizes.items():
            tokens[name] = SizingToken(
                name,
                value,
                TokenMetadata(
                    description=f"Special size value: {value}",
                    token_type=TokenType.PRIMITIVE,
                    tags={'sizing', 'special'}
                )
            )
        
        return tokens
    
    @classmethod
    def create_all_primitives(cls) -> Dict[str, Any]:
        """Create all primitive tokens"""
        all_tokens = {}
        
        all_tokens.update(cls.create_color_palette())
        all_tokens.update(cls.create_spacing_scale())
        all_tokens.update(cls.create_typography_scale())
        all_tokens.update(cls.create_sizing_scale())
        
        return all_tokens 
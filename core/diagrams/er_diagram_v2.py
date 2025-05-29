#!/usr/bin/env python3
"""
Entity Relationship Diagram Generator for Social Download Manager v2.0

Generates a visual ER diagram showing the relationships between entities
in the new database schema design.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

def create_er_diagram():
    """Create and display the ER diagram for the new schema"""
    
    # Set up the figure
    fig, ax = plt.subplots(1, 1, figsize=(20, 16))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    # Define colors
    entity_color = '#E8F4FD'
    primary_key_color = '#FFE6E6'
    foreign_key_color = '#E6F7E6'
    junction_color = '#FFF0E6'
    
    # Entity definitions with positions and attributes
    entities = {
        'platforms': {
            'pos': (15, 85),
            'size': (18, 12),
            'attributes': [
                'id (PK)',
                'name',
                'display_name', 
                'base_url',
                'api_endpoint',
                'is_active',
                'supported_content_types',
                'metadata',
                'created_at',
                'updated_at'
            ]
        },
        'content': {
            'pos': (45, 65),
            'size': (22, 20),
            'attributes': [
                'id (PK)',
                'platform_id (FK)',
                'original_url',
                'platform_content_id',
                'canonical_url',
                'title',
                'description',
                'content_type',
                'status',
                'author_name',
                'author_id',
                'duration_seconds',
                'file_size_bytes',
                'view_count',
                'like_count',
                'published_at',
                'local_file_path',
                'created_at',
                'updated_at'
            ]
        },
        'content_metadata': {
            'pos': (75, 85),
            'size': (20, 12),
            'attributes': [
                'id (PK)',
                'content_id (FK)',
                'metadata_type',
                'metadata_key',
                'metadata_value',
                'data_type',
                'parent_key',
                'created_at',
                'updated_at'
            ]
        },
        'downloads': {
            'pos': (15, 45),
            'size': (22, 18),
            'attributes': [
                'id (PK)',
                'content_id (FK)',
                'requested_quality',
                'requested_format',
                'output_directory',
                'status',
                'progress_percentage',
                'current_speed_bps',
                'final_filename',
                'final_file_path',
                'queued_at',
                'started_at',
                'completed_at',
                'error_count',
                'retry_count',
                'downloader_engine',
                'created_at',
                'updated_at'
            ]
        },
        'download_sessions': {
            'pos': (15, 15),
            'size': (20, 16),
            'attributes': [
                'id (PK)',
                'download_id (FK)',
                'session_uuid',
                'session_type',
                'bytes_downloaded',
                'total_bytes',
                'peak_speed_bps',
                'session_started_at',
                'session_ended_at',
                'user_agent',
                'headers',
                'session_status',
                'created_at',
                'updated_at'
            ]
        },
        'download_errors': {
            'pos': (45, 25),
            'size': (18, 16),
            'attributes': [
                'id (PK)',
                'download_id (FK)',
                'session_id (FK)',
                'error_type',
                'error_code',
                'error_message',
                'stack_trace',
                'request_url',
                'retry_attempt',
                'occurred_at',
                'is_resolved',
                'resolution_method',
                'created_at'
            ]
        },
        'quality_options': {
            'pos': (75, 55),
            'size': (20, 14),
            'attributes': [
                'id (PK)',
                'content_id (FK)',
                'quality_label',
                'format',
                'resolution_width',
                'resolution_height',
                'bitrate_kbps',
                'fps',
                'estimated_file_size',
                'is_available',
                'download_url',
                'expires_at',
                'created_at',
                'updated_at'
            ]
        },
        'tags': {
            'pos': (75, 25),
            'size': (18, 12),
            'attributes': [
                'id (PK)',
                'name',
                'slug',
                'description',
                'tag_type',
                'usage_count',
                'created_at',
                'updated_at'
            ]
        },
        'content_tags': {
            'pos': (60, 45),
            'size': (12, 8),
            'attributes': [
                'content_id (FK)',
                'tag_id (FK)',
                'assigned_by',
                'confidence_score',
                'created_at'
            ],
            'junction': True
        }
    }
    
    # Draw entities
    for entity_name, entity_data in entities.items():
        x, y = entity_data['pos']
        width, height = entity_data['size']
        
        # Determine entity color
        if entity_data.get('junction', False):
            color = junction_color
        else:
            color = entity_color
        
        # Draw entity box
        entity_box = FancyBboxPatch(
            (x - width/2, y - height/2),
            width, height,
            boxstyle="round,pad=0.5",
            facecolor=color,
            edgecolor='black',
            linewidth=1.5
        )
        ax.add_patch(entity_box)
        
        # Draw entity name
        ax.text(x, y + height/2 - 2, entity_name.upper(), 
                ha='center', va='center', fontweight='bold', fontsize=10)
        
        # Draw attributes
        attr_y_start = y + height/2 - 4
        for i, attr in enumerate(entity_data['attributes']):
            attr_y = attr_y_start - i * 1.2
            
            # Color code attributes
            if '(PK)' in attr:
                attr_color = 'red'
                attr_weight = 'bold'
            elif '(FK)' in attr:
                attr_color = 'blue'
                attr_weight = 'normal'
            else:
                attr_color = 'black'
                attr_weight = 'normal'
            
            ax.text(x - width/2 + 1, attr_y, attr, 
                   ha='left', va='center', fontsize=8,
                   color=attr_color, fontweight=attr_weight)
    
    # Define relationships
    relationships = [
        # (from_entity, to_entity, relationship_type, label)
        ('platforms', 'content', 'one_to_many', '1:M'),
        ('content', 'content_metadata', 'one_to_many', '1:M'),
        ('content', 'downloads', 'one_to_many', '1:M'),
        ('content', 'quality_options', 'one_to_many', '1:M'),
        ('downloads', 'download_sessions', 'one_to_many', '1:M'),
        ('downloads', 'download_errors', 'one_to_many', '1:M'),
        ('download_sessions', 'download_errors', 'one_to_many', '1:M'),
        ('content', 'content_tags', 'one_to_many', '1:M'),
        ('tags', 'content_tags', 'one_to_many', '1:M')
    ]
    
    # Draw relationships
    for from_entity, to_entity, rel_type, label in relationships:
        from_pos = entities[from_entity]['pos']
        to_pos = entities[to_entity]['pos']
        
        # Calculate connection points
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        
        # Determine edge points for cleaner lines
        from_size = entities[from_entity]['size']
        to_size = entities[to_entity]['size']
        
        # Calculate edge connection points
        if from_x < to_x:  # Connection goes right
            from_x += from_size[0]/2
            to_x -= to_size[0]/2
        else:  # Connection goes left
            from_x -= from_size[0]/2
            to_x += to_size[0]/2
            
        if from_y > to_y:  # Connection goes down
            from_y -= from_size[1]/2
            to_y += to_size[1]/2
        else:  # Connection goes up
            from_y += from_size[1]/2
            to_y -= to_size[1]/2
        
        # Draw connection line
        line = ConnectionPatch(
            (from_x, from_y), (to_x, to_y),
            "data", "data",
            arrowstyle="->",
            shrinkA=5, shrinkB=5,
            mutation_scale=20,
            fc="gray", ec="gray",
            linewidth=1.5
        )
        ax.add_patch(line)
        
        # Add relationship label
        mid_x = (from_x + to_x) / 2
        mid_y = (from_y + to_y) / 2
        ax.text(mid_x, mid_y, label, 
               ha='center', va='center', fontsize=8,
               bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
    
    # Add title and legend
    ax.text(50, 95, 'Social Download Manager v2.0 - Entity Relationship Diagram', 
           ha='center', va='center', fontweight='bold', fontsize=16)
    
    # Add legend
    legend_x, legend_y = 5, 10
    legend_items = [
        ('Entity', entity_color, 'black'),
        ('Junction Table', junction_color, 'black'),
        ('Primary Key', 'white', 'red'),
        ('Foreign Key', 'white', 'blue')
    ]
    
    for i, (label, bg_color, text_color) in enumerate(legend_items):
        legend_item_y = legend_y - i * 2
        legend_box = FancyBboxPatch(
            (legend_x, legend_item_y - 0.5),
            8, 1,
            boxstyle="round,pad=0.1",
            facecolor=bg_color,
            edgecolor='black',
            linewidth=1
        )
        ax.add_patch(legend_box)
        ax.text(legend_x + 4, legend_item_y, label, 
               ha='center', va='center', fontsize=8,
               color=text_color, fontweight='bold')
    
    # Add cardinality explanation
    ax.text(85, 10, 'Relationships:\n1:M = One-to-Many\nM:M = Many-to-Many (via junction)', 
           ha='left', va='top', fontsize=8,
           bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.8))
    
    plt.tight_layout()
    return fig

def save_diagram():
    """Generate and save the ER diagram"""
    fig = create_er_diagram()
    
    # Save in multiple formats
    output_dir = "core/diagrams/"
    
    # High-resolution PNG
    fig.savefig(f"{output_dir}er_diagram_v2.png", 
                dpi=300, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    # PDF for vector graphics
    fig.savefig(f"{output_dir}er_diagram_v2.pdf", 
                bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    # SVG for web use
    fig.savefig(f"{output_dir}er_diagram_v2.svg", 
                bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    
    print("ER Diagram saved in PNG, PDF, and SVG formats")
    plt.show()

if __name__ == "__main__":
    save_diagram() 
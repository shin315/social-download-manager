"""
Script to remove Action column code from downloaded_videos_tab.py
"""

def main():
    # Read the file
    file_path = 'ui/downloaded_videos_tab.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the Action widget code
    start_marker = '            # Action (Open and Delete) column'
    end_marker = '            self.downloads_table.setCellWidget(idx, 9, action_widget)'
    
    start_pos = content.find(start_marker)
    if start_pos == -1:
        print("Action column code not found! Already removed?")
        return
    
    end_pos = content.find(end_marker, start_pos)
    if end_pos == -1:
        print("End of Action column code not found!")
        return
    
    end_pos += len(end_marker)
    
    # Replace the Action widget code with a comment
    new_content = (
        content[:start_pos] + 
        '            # Action column has been removed\n' +
        '            # Functionality now available through context menu\n\n' +
        content[end_pos:]
    )
    
    # Write the modified content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Action column code successfully removed!")

if __name__ == "__main__":
    main() 
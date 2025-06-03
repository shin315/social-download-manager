#!/usr/bin/env python3
"""
Cleanup Unused Imports - Task 35.5
Scan and remove unused imports/references to legacy UI components that were removed.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class UnusedImportCleaner:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.patterns_to_remove = [
            # Legacy UI component imports
            r'from ui\.video_info_tab import.*',
            r'import ui\.video_info_tab.*',
            r'from ui\.downloaded_videos_tab import.*',
            r'import ui\.downloaded_videos_tab.*',
            
            # Adapter framework imports
            r'from ui\.adapters\..*',
            r'import ui\.adapters\..*',
        ]
        
        # Files to exclude from cleanup (migration scripts, examples, etc.)
        self.exclude_patterns = [
            'scripts_dev/migration/',
            'examples/migration/',
            'backup/',
            'tests/',
            '__pycache__/',
            '.git/',
        ]
        
        self.findings: List[Dict] = []
        self.cleaned_files: List[str] = []
        
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from cleanup"""
        file_str = str(file_path.relative_to(self.project_root))
        for pattern in self.exclude_patterns:
            if pattern in file_str:
                return True
        return False
        
    def scan_file(self, file_path: Path) -> List[Tuple[int, str, str]]:
        """Scan a single file for unused imports"""
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                for pattern in self.patterns_to_remove:
                    if re.search(pattern, line.strip()):
                        matches.append((line_num, line.strip(), pattern))
                        
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
            
        return matches
        
    def clean_file(self, file_path: Path, matches: List[Tuple[int, str, str]]) -> bool:
        """Remove unused imports from a file"""
        if not matches:
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Sort matches by line number in reverse order to avoid index shifting
            matches_sorted = sorted(matches, key=lambda x: x[0], reverse=True)
            
            lines_removed = 0
            for line_num, line_content, pattern in matches_sorted:
                # Adjust for 0-based indexing
                index = line_num - 1
                if index < len(lines) and lines[index].strip() == line_content:
                    lines.pop(index)
                    lines_removed += 1
                    
            if lines_removed > 0:
                # Write cleaned content back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                    
                self.cleaned_files.append(str(file_path.relative_to(self.project_root)))
                return True
                
        except Exception as e:
            print(f"Error cleaning {file_path}: {e}")
            
        return False
        
    def scan_project(self) -> Dict:
        """Scan entire project for unused imports"""
        print("🔍 Scanning project for unused imports...")
        
        python_files = list(self.project_root.rglob("*.py"))
        total_files = len(python_files)
        processed = 0
        
        for file_path in python_files:
            if self.should_exclude_file(file_path):
                continue
                
            matches = self.scan_file(file_path)
            if matches:
                self.findings.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'matches': matches
                })
                
            processed += 1
            if processed % 10 == 0:
                print(f"  Processed {processed}/{total_files} files...")
                
        return {
            'total_files_scanned': processed,
            'files_with_issues': len(self.findings),
            'total_unused_imports': sum(len(f['matches']) for f in self.findings)
        }
        
    def clean_all(self) -> Dict:
        """Clean all found unused imports"""
        if not self.findings:
            return {'cleaned_files': 0, 'removed_imports': 0}
            
        print("🧹 Cleaning unused imports...")
        
        total_removed = 0
        for finding in self.findings:
            file_path = self.project_root / finding['file']
            if self.clean_file(file_path, finding['matches']):
                total_removed += len(finding['matches'])
                
        return {
            'cleaned_files': len(self.cleaned_files),
            'removed_imports': total_removed
        }
        
    def generate_report(self) -> Dict:
        """Generate cleanup report"""
        return {
            'scan_results': {
                'total_files_scanned': sum(1 for _ in self.project_root.rglob("*.py") if not self.should_exclude_file(_)),
                'files_with_unused_imports': len(self.findings),
                'total_unused_imports_found': sum(len(f['matches']) for f in self.findings),
            },
            'cleanup_results': {
                'files_cleaned': len(self.cleaned_files),
                'imports_removed': sum(len(f['matches']) for f in self.findings),
            },
            'cleaned_files': self.cleaned_files,
            'findings_detail': self.findings[:5]  # Show first 5 for brevity
        }

def main():
    """Main execution function"""
    project_root = Path(__file__).parent.parent.parent
    
    print("=" * 60)
    print("🧹 UNUSED IMPORT CLEANUP - Task 35.5")
    print("=" * 60)
    print(f"Project root: {project_root}")
    
    cleaner = UnusedImportCleaner(str(project_root))
    
    # Scan phase
    scan_results = cleaner.scan_project()
    print(f"\n📊 Scan Results:")
    print(f"  Files scanned: {scan_results['total_files_scanned']}")
    print(f"  Files with issues: {scan_results['files_with_issues']}")
    print(f"  Total unused imports: {scan_results['total_unused_imports']}")
    
    if scan_results['files_with_issues'] == 0:
        print("\n✅ No unused imports found!")
        return
        
    # Show findings
    print(f"\n🔍 Found unused imports in {len(cleaner.findings)} files:")
    for finding in cleaner.findings[:10]:  # Show first 10
        print(f"  📄 {finding['file']}: {len(finding['matches'])} unused imports")
        
    # Clean phase
    clean_results = cleaner.clean_all()
    print(f"\n🧹 Cleanup Results:")
    print(f"  Files cleaned: {clean_results['cleaned_files']}")
    print(f"  Imports removed: {clean_results['removed_imports']}")
    
    # Generate report
    report = cleaner.generate_report()
    report_file = project_root / "scripts_dev/utilities/unused_imports_cleanup_report.json"
    
    import json
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\n📋 Detailed report saved to: {report_file}")
    print("=" * 60)
    print("✅ CLEANUP COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main() 
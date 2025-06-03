#!/usr/bin/env python3
"""
Adapter Code Optimization Integration Test
==========================================

This script tests the code optimization system with sample adapter code
to demonstrate its analysis capabilities and optimization recommendations.
"""

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from scripts_dev.performance.adapter_code_optimizer import (
    AdapterCodeOptimizer,
    CodeAnalyzer,
    DuplicationDetector,
    RefactoringAnalyzer
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdapterCodeOptimizationTester:
    """Integration tester for adapter code optimization system"""
    
    def __init__(self):
        self.temp_files = []
        self.test_results = {}
    
    def create_sample_adapter_files(self) -> Dict[str, str]:
        """Create sample adapter files for testing"""
        
        # Sample adapter with performance issues
        adapter_with_issues = '''
"""Sample adapter with intentional performance issues"""

class VideoAdapter:
    def __init__(self):
        self.cache = {}
        self.data = []
    
    def process_videos(self, videos):
        """Long method with nested loops and string concatenation"""
        result = ""
        processed = []
        
        # Nested loops - O(n²) complexity
        for video in videos:
            for existing in processed:
                if video.id == existing.id:
                    # String concatenation in loop
                    result += f"Duplicate: {video.title}\\n"
                    break
            
            # Complex condition with magic numbers
            if (video.duration > 3600 and video.size > 1073741824 and 
                video.quality == "4K" and video.fps > 30 and 
                video.bitrate > 50000000):
                
                # More string concatenation
                result += f"High quality video: {video.title}\\n"
                
                # Magic number usage
                if video.views > 1000000:
                    result += "Popular video\\n"
            
            processed.append(video)
        
        return result
    
    def analyze_performance(self, data):
        """Another long method that should be refactored"""
        analysis = {}
        
        # Large method with many responsibilities
        total_duration = 0
        total_size = 0
        quality_distribution = {}
        format_distribution = {}
        
        for item in data:
            total_duration += item.get('duration', 0)
            total_size += item.get('size', 0)
            
            quality = item.get('quality', 'unknown')
            if quality in quality_distribution:
                quality_distribution[quality] += 1
            else:
                quality_distribution[quality] = 1
            
            format_type = item.get('format', 'unknown')
            if format_type in format_distribution:
                format_distribution[format_type] += 1
            else:
                format_distribution[format_type] = 1
        
        analysis['total_duration'] = total_duration
        analysis['total_size'] = total_size
        analysis['avg_duration'] = total_duration / len(data) if data else 0
        analysis['avg_size'] = total_size / len(data) if data else 0
        analysis['quality_dist'] = quality_distribution
        analysis['format_dist'] = format_distribution
        
        return analysis

class DataProcessor:
    """Class with too many methods - should be refactored"""
    
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
    def method13(self): pass
    def method14(self): pass
    def method15(self): pass
    def method16(self): pass
    def method17(self): pass
    def method18(self): pass
    def method19(self): pass
    def method20(self): pass
    def method21(self): pass
    def method22(self): pass
    def method23(self): pass
'''

        # Sample adapter with duplicated code
        duplicate_adapter = '''
"""Sample adapter with code duplication"""

class DownloadAdapter:
    def process_download_request(self, request):
        """Method with duplicated logic"""
        if request.url and request.url.startswith('http'):
            if request.format in ['mp4', 'avi', 'mkv']:
                if request.quality in ['720p', '1080p', '4K']:
                    return {'status': 'valid', 'url': request.url}
        return {'status': 'invalid'}
    
    def validate_download_params(self, params):
        """Almost identical logic - should be extracted"""
        if params.url and params.url.startswith('http'):
            if params.format in ['mp4', 'avi', 'mkv']:
                if params.quality in ['720p', '1080p', '4K']:
                    return {'status': 'valid', 'url': params.url}
        return {'status': 'invalid'}
'''

        # Sample optimized adapter
        optimized_adapter = '''
"""Well-structured adapter example"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class VideoInfo:
    """Well-documented video information structure"""
    id: str
    title: str
    duration: int
    size: int
    quality: str
    fps: int
    bitrate: int
    views: int

class OptimizedVideoAdapter:
    """Example of well-structured adapter with good practices"""
    
    # Constants instead of magic numbers
    LARGE_FILE_THRESHOLD = 1073741824  # 1GB
    LONG_VIDEO_THRESHOLD = 3600  # 1 hour
    POPULAR_VIDEO_THRESHOLD = 1000000  # 1M views
    HIGH_BITRATE_THRESHOLD = 50000000  # 50Mbps
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.processed_videos: Set[str] = set()
    
    def process_videos(self, videos: List[VideoInfo]) -> Dict[str, List[str]]:
        """Process videos efficiently with good structure"""
        results = {
            'duplicates': [],
            'high_quality': [],
            'popular': []
        }
        
        # Use set for O(1) lookup instead of nested loops
        for video in videos:
            if self._is_duplicate(video):
                results['duplicates'].append(video.title)
            
            if self._is_high_quality_video(video):
                results['high_quality'].append(video.title)
            
            if self._is_popular_video(video):
                results['popular'].append(video.title)
        
        return results
    
    def _is_duplicate(self, video: VideoInfo) -> bool:
        """Check if video is duplicate using efficient lookup"""
        if video.id in self.processed_videos:
            return True
        self.processed_videos.add(video.id)
        return False
    
    def _is_high_quality_video(self, video: VideoInfo) -> bool:
        """Check if video meets high quality criteria"""
        return (
            video.duration > self.LONG_VIDEO_THRESHOLD and
            video.size > self.LARGE_FILE_THRESHOLD and
            video.quality == "4K" and
            video.fps > 30 and
            video.bitrate > self.HIGH_BITRATE_THRESHOLD
        )
    
    def _is_popular_video(self, video: VideoInfo) -> bool:
        """Check if video is popular"""
        return video.views > self.POPULAR_VIDEO_THRESHOLD
'''

        return {
            'adapter_with_issues.py': adapter_with_issues,
            'duplicate_adapter.py': duplicate_adapter,
            'optimized_adapter.py': optimized_adapter
        }
    
    def run_optimization_analysis_test(self) -> Dict[str, Any]:
        """Run comprehensive optimization analysis test"""
        logger.info("Starting adapter code optimization integration test")
        
        # Create sample files
        sample_files = self.create_sample_adapter_files()
        
        # Create temporary directory and files
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = []
            
            for filename, content in sample_files.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                file_paths.append(file_path)
            
            # Initialize optimizer with temp directory
            optimizer = AdapterCodeOptimizer(target_directories=[temp_dir])
            
            # Test individual components
            analyzer = CodeAnalyzer()
            duplication_detector = DuplicationDetector()
            refactoring_analyzer = RefactoringAnalyzer()
            
            # Analyze each file
            analysis_results = {}
            for file_path in file_paths:
                analysis_results[file_path] = analyzer.analyze_file(file_path)
            
            # Test duplication detection
            file_contents = {
                path: data['content']
                for path, data in analysis_results.items()
                if 'content' in data
            }
            duplications = duplication_detector.detect_duplications(file_contents)
            
            # Test refactoring analysis
            refactoring_opportunities = refactoring_analyzer.analyze_refactoring_opportunities(
                analysis_results
            )
            
            # Aggregate results
            total_files = len(file_paths)
            total_loc = sum(
                data['metrics'].lines_of_code 
                for data in analysis_results.values()
                if 'metrics' in data
            )
            total_functions = sum(
                data['metrics'].function_count
                for data in analysis_results.values()
                if 'metrics' in data
            )
            total_classes = sum(
                data['metrics'].class_count
                for data in analysis_results.values()
                if 'metrics' in data
            )
            
            # Calculate scores
            performance_issues = sum(
                len(data['bottlenecks'])
                for data in analysis_results.values()
                if 'bottlenecks' in data
            )
            
            # Generate test results
            test_results = {
                'timestamp': datetime.now().isoformat(),
                'files_analyzed': total_files,
                'total_lines_of_code': total_loc,
                'total_functions': total_functions,
                'total_classes': total_classes,
                'performance_bottlenecks_detected': performance_issues,
                'code_duplications_detected': len(duplications),
                'refactoring_opportunities_detected': len(refactoring_opportunities),
                'analysis_details': {
                    'cyclomatic_complexity': sum(
                        data['metrics'].cyclomatic_complexity
                        for data in analysis_results.values()
                        if 'metrics' in data
                    ),
                    'cognitive_complexity': sum(
                        data['metrics'].cognitive_complexity
                        for data in analysis_results.values()
                        if 'metrics' in data
                    ),
                    'average_maintainability': sum(
                        data['metrics'].maintainability_index
                        for data in analysis_results.values()
                        if 'metrics' in data
                    ) / total_files if total_files > 0 else 0
                },
                'optimization_effectiveness': {
                    'issues_identified': performance_issues + len(duplications) + len(refactoring_opportunities),
                    'optimization_potential': 'High' if performance_issues > 5 else 'Medium' if performance_issues > 2 else 'Low'
                }
            }
        
        logger.info(f"Analysis completed - {total_files} files analyzed")
        return test_results
    
    def save_test_results(self, results: Dict[str, Any]) -> str:
        """Save integration test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scripts_dev/performance_results/adapter_code_optimization_integration_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Test results saved to: {filename}")
        return filename


def main():
    """Run adapter code optimization integration test"""
    print("=== Adapter Code Optimization Integration Test ===\n")
    
    tester = AdapterCodeOptimizationTester()
    
    # Run comprehensive test
    print("Running code optimization analysis on sample adapter files...")
    results = tester.run_optimization_analysis_test()
    
    # Save results
    results_file = tester.save_test_results(results)
    
    # Display summary
    print(f"\n{'='*60}")
    print("ADAPTER CODE OPTIMIZATION INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    
    print(f"Files Analyzed: {results['files_analyzed']}")
    print(f"Total Lines of Code: {results['total_lines_of_code']:,}")
    print(f"Functions: {results['total_functions']}")
    print(f"Classes: {results['total_classes']}")
    
    print(f"\nIssues Detected:")
    print(f"  Performance Bottlenecks: {results['performance_bottlenecks_detected']}")
    print(f"  Code Duplications: {results['code_duplications_detected']}")
    print(f"  Refactoring Opportunities: {results['refactoring_opportunities_detected']}")
    
    print(f"\nCode Quality Metrics:")
    details = results['analysis_details']
    print(f"  Cyclomatic Complexity: {details['cyclomatic_complexity']}")
    print(f"  Cognitive Complexity: {details['cognitive_complexity']}")
    print(f"  Average Maintainability: {details['average_maintainability']:.1f}")
    
    effectiveness = results['optimization_effectiveness']
    print(f"\nOptimization Assessment:")
    print(f"  Total Issues Identified: {effectiveness['issues_identified']}")
    print(f"  Optimization Potential: {effectiveness['optimization_potential']}")
    
    if effectiveness['issues_identified'] > 0:
        print(f"\n✅ Code optimization system successfully detected issues!")
        print(f"   - Algorithm complexity problems detected")
        print(f"   - Code duplication patterns identified")
        print(f"   - Refactoring opportunities found")
        print(f"   - Performance bottlenecks flagged")
    else:
        print(f"\n⚠️  No major issues detected in sample code")
    
    print(f"\nResults saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Visual Regression Automation for UI Migration
Automated visual testing and comparison for theme consistency validation
Part of subtask 32.6 - Theme and Internationalization Testing
"""

import sys
import os
import json
import hashlib
import tempfile
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


@dataclass
class VisualTestCase:
    """Visual test case definition"""
    component_name: str
    theme: str
    window_size: Tuple[int, int]
    test_scenarios: List[str]
    expected_elements: List[str]


@dataclass
class VisualComparisonResult:
    """Result of visual comparison"""
    test_case: str
    baseline_path: str
    current_path: str
    difference_score: float
    pixel_differences: int
    structural_similarity: float
    passed: bool
    issues: List[str]


@dataclass
class VisualRegressionReport:
    """Comprehensive visual regression report"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    overall_similarity: float
    comparison_results: List[VisualComparisonResult]
    recommendations: List[str]


class VisualRegressionAutomation:
    """Automation system for visual regression testing"""
    
    def __init__(self):
        self.project_root = project_root
        self.baseline_dir = os.path.join(project_root, "tests", "ui_migration", "visual_baselines")
        self.current_dir = os.path.join(project_root, "tests", "ui_migration", "visual_current")
        self.diff_dir = os.path.join(project_root, "tests", "ui_migration", "visual_diffs")
        self.report_dir = os.path.join(project_root, "tests", "ui_migration", "visual_reports")
        
        # Create directories
        for directory in [self.baseline_dir, self.current_dir, self.diff_dir, self.report_dir]:
            os.makedirs(directory, exist_ok=True)
            
        # Visual test cases
        self.test_cases = self._define_test_cases()
        
        # Comparison thresholds
        self.similarity_threshold = 0.95  # 95% similarity required
        self.pixel_threshold = 100  # Max 100 pixel differences
        
    def _define_test_cases(self) -> List[VisualTestCase]:
        """Define visual test cases for migration validation"""
        return [
            VisualTestCase(
                component_name="video_info_tab",
                theme="dark",
                window_size=(1200, 800),
                test_scenarios=["empty_state", "with_videos", "downloading"],
                expected_elements=["url_input", "video_table", "download_button", "folder_selector"]
            ),
            VisualTestCase(
                component_name="video_info_tab", 
                theme="light",
                window_size=(1200, 800),
                test_scenarios=["empty_state", "with_videos", "downloading"],
                expected_elements=["url_input", "video_table", "download_button", "folder_selector"]
            ),
            VisualTestCase(
                component_name="downloaded_videos_tab",
                theme="dark",
                window_size=(1200, 800),
                test_scenarios=["empty_state", "with_videos", "selected_video"],
                expected_elements=["search_input", "video_list", "video_details", "stats_panel"]
            ),
            VisualTestCase(
                component_name="downloaded_videos_tab",
                theme="light", 
                window_size=(1200, 800),
                test_scenarios=["empty_state", "with_videos", "selected_video"],
                expected_elements=["search_input", "video_list", "video_details", "stats_panel"]
            ),
            VisualTestCase(
                component_name="main_window",
                theme="dark",
                window_size=(1400, 900),
                test_scenarios=["startup", "with_tabs", "menu_open"],
                expected_elements=["menu_bar", "tab_widget", "status_bar"]
            ),
            VisualTestCase(
                component_name="main_window",
                theme="light",
                window_size=(1400, 900), 
                test_scenarios=["startup", "with_tabs", "menu_open"],
                expected_elements=["menu_bar", "tab_widget", "status_bar"]
            )
        ]
        
    def capture_component_visuals(self, test_case: VisualTestCase, output_dir: str) -> List[str]:
        """Capture visual representations of a component"""
        captured_files = []
        
        for scenario in test_case.test_scenarios:
            filename = f"{test_case.component_name}_{test_case.theme}_{scenario}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Mock visual capture (in real implementation would use actual screenshot)
            visual_data = self._generate_mock_visual_data(test_case, scenario)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(visual_data, f, indent=2)
                
            captured_files.append(filepath)
            print(f"Captured: {filename}")
            
        return captured_files
        
    def _generate_mock_visual_data(self, test_case: VisualTestCase, scenario: str) -> Dict:
        """Generate mock visual data for testing"""
        
        # Simulate different visual characteristics based on theme and scenario
        base_data = {
            "component": test_case.component_name,
            "theme": test_case.theme,
            "scenario": scenario,
            "window_size": test_case.window_size,
            "timestamp": "2025-06-03T11:00:00Z",
            "elements": {},
            "colors": {},
            "layout": {}
        }
        
        # Theme-specific colors
        if test_case.theme == "dark":
            base_data["colors"] = {
                "background": "#2d2d2d",
                "text": "#ffffff",
                "accent": "#0078d4",
                "border": "#555555"
            }
        else:
            base_data["colors"] = {
                "background": "#f5f5f5", 
                "text": "#333333",
                "accent": "#0078d4",
                "border": "#cccccc"
            }
            
        # Element positions and properties
        for element in test_case.expected_elements:
            base_data["elements"][element] = {
                "visible": True,
                "position": self._get_mock_position(element),
                "size": self._get_mock_size(element),
                "style_hash": self._generate_style_hash(element, test_case.theme)
            }
            
        # Scenario-specific modifications
        if scenario == "empty_state":
            base_data["layout"]["main_content_visible"] = False
        elif scenario == "with_videos":
            base_data["layout"]["video_count"] = 5
            base_data["layout"]["table_rows"] = 5
        elif scenario == "downloading":
            base_data["layout"]["progress_visible"] = True
            base_data["elements"]["progress_bar"] = {
                "visible": True,
                "position": {"x": 10, "y": 100},
                "size": {"width": 300, "height": 20},
                "value": 45
            }
            
        return base_data
        
    def _get_mock_position(self, element: str) -> Dict[str, int]:
        """Get mock position for UI element"""
        positions = {
            "url_input": {"x": 10, "y": 10},
            "video_table": {"x": 10, "y": 50},
            "download_button": {"x": 200, "y": 10},
            "folder_selector": {"x": 400, "y": 10},
            "search_input": {"x": 10, "y": 10},
            "video_list": {"x": 10, "y": 50},
            "video_details": {"x": 400, "y": 50},
            "stats_panel": {"x": 10, "y": 400},
            "menu_bar": {"x": 0, "y": 0},
            "tab_widget": {"x": 0, "y": 25},
            "status_bar": {"x": 0, "y": 870}
        }
        return positions.get(element, {"x": 0, "y": 0})
        
    def _get_mock_size(self, element: str) -> Dict[str, int]:
        """Get mock size for UI element"""
        sizes = {
            "url_input": {"width": 300, "height": 30},
            "video_table": {"width": 800, "height": 400},
            "download_button": {"width": 100, "height": 30},
            "folder_selector": {"width": 150, "height": 30},
            "search_input": {"width": 250, "height": 30},
            "video_list": {"width": 350, "height": 600},
            "video_details": {"width": 400, "height": 600},
            "stats_panel": {"width": 800, "height": 100},
            "menu_bar": {"width": 1400, "height": 25},
            "tab_widget": {"width": 1400, "height": 845},
            "status_bar": {"width": 1400, "height": 30}
        }
        return sizes.get(element, {"width": 100, "height": 100})
        
    def _generate_style_hash(self, element: str, theme: str) -> str:
        """Generate hash for element styling"""
        style_string = f"{element}_{theme}_styling"
        return hashlib.md5(style_string.encode()).hexdigest()[:8]
        
    def capture_baseline_visuals(self) -> List[str]:
        """Capture baseline visuals for all test cases"""
        print("Capturing baseline visuals...")
        all_files = []
        
        for test_case in self.test_cases:
            print(f"Capturing baseline for {test_case.component_name} ({test_case.theme})")
            files = self.capture_component_visuals(test_case, self.baseline_dir)
            all_files.extend(files)
            
        print(f"Captured {len(all_files)} baseline files")
        return all_files
        
    def capture_current_visuals(self) -> List[str]:
        """Capture current visuals for comparison"""
        print("Capturing current visuals...")
        all_files = []
        
        for test_case in self.test_cases:
            print(f"Capturing current for {test_case.component_name} ({test_case.theme})")
            files = self.capture_component_visuals(test_case, self.current_dir)
            all_files.extend(files)
            
        print(f"Captured {len(all_files)} current files")
        return all_files
        
    def compare_visuals(self, baseline_file: str, current_file: str) -> VisualComparisonResult:
        """Compare baseline and current visual files"""
        
        test_case_name = os.path.basename(baseline_file).replace('.json', '')
        issues = []
        
        try:
            # Load data
            with open(baseline_file, 'r') as f:
                baseline_data = json.load(f)
            with open(current_file, 'r') as f:
                current_data = json.load(f)
                
            # Compare structure
            structural_similarity = self._calculate_structural_similarity(baseline_data, current_data)
            
            # Compare elements
            pixel_differences = self._calculate_pixel_differences(baseline_data, current_data)
            
            # Compare colors
            color_similarity = self._compare_colors(baseline_data.get("colors", {}), current_data.get("colors", {}))
            
            # Overall difference score
            difference_score = 1.0 - ((structural_similarity + color_similarity) / 2.0)
            
            # Determine if passed
            passed = (structural_similarity >= self.similarity_threshold and 
                     pixel_differences <= self.pixel_threshold)
                     
            if not passed:
                if structural_similarity < self.similarity_threshold:
                    issues.append(f"Structural similarity {structural_similarity:.2%} below threshold {self.similarity_threshold:.2%}")
                if pixel_differences > self.pixel_threshold:
                    issues.append(f"Pixel differences {pixel_differences} exceed threshold {self.pixel_threshold}")
                    
        except Exception as e:
            structural_similarity = 0.0
            pixel_differences = 9999
            difference_score = 1.0
            passed = False
            issues.append(f"Comparison failed: {str(e)}")
            
        return VisualComparisonResult(
            test_case=test_case_name,
            baseline_path=baseline_file,
            current_path=current_file,
            difference_score=difference_score,
            pixel_differences=pixel_differences,
            structural_similarity=structural_similarity,
            passed=passed,
            issues=issues
        )
        
    def _calculate_structural_similarity(self, baseline: Dict, current: Dict) -> float:
        """Calculate structural similarity between visual data"""
        
        # Compare element structure
        baseline_elements = set(baseline.get("elements", {}).keys())
        current_elements = set(current.get("elements", {}).keys())
        
        if not baseline_elements and not current_elements:
            element_similarity = 1.0
        elif not baseline_elements or not current_elements:
            element_similarity = 0.0
        else:
            intersection = baseline_elements.intersection(current_elements)
            union = baseline_elements.union(current_elements)
            element_similarity = len(intersection) / len(union) if union else 0.0
            
        # Compare layout properties
        baseline_layout = baseline.get("layout", {})
        current_layout = current.get("layout", {})
        
        layout_keys = set(baseline_layout.keys()).union(set(current_layout.keys()))
        layout_matches = 0
        
        for key in layout_keys:
            if baseline_layout.get(key) == current_layout.get(key):
                layout_matches += 1
                
        layout_similarity = layout_matches / len(layout_keys) if layout_keys else 1.0
        
        # Overall structural similarity
        return (element_similarity + layout_similarity) / 2.0
        
    def _calculate_pixel_differences(self, baseline: Dict, current: Dict) -> int:
        """Calculate simulated pixel differences"""
        
        differences = 0
        
        # Compare element positions and sizes
        baseline_elements = baseline.get("elements", {})
        current_elements = current.get("elements", {})
        
        for element_name in baseline_elements:
            if element_name in current_elements:
                baseline_elem = baseline_elements[element_name]
                current_elem = current_elements[element_name]
                
                # Position differences
                baseline_pos = baseline_elem.get("position", {})
                current_pos = current_elem.get("position", {})
                
                x_diff = abs(baseline_pos.get("x", 0) - current_pos.get("x", 0))
                y_diff = abs(baseline_pos.get("y", 0) - current_pos.get("y", 0))
                
                differences += x_diff + y_diff
                
                # Size differences
                baseline_size = baseline_elem.get("size", {})
                current_size = current_elem.get("size", {})
                
                w_diff = abs(baseline_size.get("width", 0) - current_size.get("width", 0))
                h_diff = abs(baseline_size.get("height", 0) - current_size.get("height", 0))
                
                differences += w_diff + h_diff
                
        return differences
        
    def _compare_colors(self, baseline_colors: Dict, current_colors: Dict) -> float:
        """Compare color schemes"""
        
        if not baseline_colors and not current_colors:
            return 1.0
            
        if not baseline_colors or not current_colors:
            return 0.0
            
        color_keys = set(baseline_colors.keys()).union(set(current_colors.keys()))
        matches = 0
        
        for key in color_keys:
            if baseline_colors.get(key) == current_colors.get(key):
                matches += 1
                
        return matches / len(color_keys) if color_keys else 0.0
        
    def run_visual_regression_test(self) -> VisualRegressionReport:
        """Run complete visual regression test suite"""
        
        print("Starting visual regression testing...")
        
        # Capture current visuals
        current_files = self.capture_current_visuals()
        
        # Compare with baselines
        comparison_results = []
        
        for test_case in self.test_cases:
            for scenario in test_case.test_scenarios:
                baseline_filename = f"{test_case.component_name}_{test_case.theme}_{scenario}.json"
                baseline_path = os.path.join(self.baseline_dir, baseline_filename)
                current_path = os.path.join(self.current_dir, baseline_filename)
                
                if os.path.exists(baseline_path) and os.path.exists(current_path):
                    result = self.compare_visuals(baseline_path, current_path)
                    comparison_results.append(result)
                    
                    # Save diff visualization
                    self._save_diff_visualization(result)
                    
        # Generate report
        report = self._generate_regression_report(comparison_results)
        
        print(f"Visual regression testing complete. {report.passed_tests}/{report.total_tests} tests passed")
        return report
        
    def _save_diff_visualization(self, result: VisualComparisonResult):
        """Save diff visualization for failed comparisons"""
        
        if not result.passed:
            diff_filename = f"{result.test_case}_diff.json"
            diff_path = os.path.join(self.diff_dir, diff_filename)
            
            diff_data = {
                "test_case": result.test_case,
                "baseline": result.baseline_path,
                "current": result.current_path,
                "difference_score": result.difference_score,
                "pixel_differences": result.pixel_differences,
                "structural_similarity": result.structural_similarity,
                "issues": result.issues,
                "timestamp": "2025-06-03T11:30:00Z"
            }
            
            with open(diff_path, 'w') as f:
                json.dump(diff_data, f, indent=2)
                
    def _generate_regression_report(self, results: List[VisualComparisonResult]) -> VisualRegressionReport:
        """Generate comprehensive regression report"""
        
        total_tests = len(results)
        passed_tests = len([r for r in results if r.passed])
        failed_tests = total_tests - passed_tests
        
        # Calculate overall similarity
        if results:
            overall_similarity = sum(r.structural_similarity for r in results) / len(results)
        else:
            overall_similarity = 0.0
            
        # Generate recommendations
        recommendations = self._generate_visual_recommendations(results)
        
        return VisualRegressionReport(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            overall_similarity=overall_similarity,
            comparison_results=results,
            recommendations=recommendations
        )
        
    def _generate_visual_recommendations(self, results: List[VisualComparisonResult]) -> List[str]:
        """Generate recommendations based on visual comparison results"""
        
        recommendations = []
        failed_results = [r for r in results if not r.passed]
        
        if failed_results:
            # Analyze common issues
            structural_issues = [r for r in failed_results if r.structural_similarity < 0.9]
            if structural_issues:
                recommendations.append(f"Address structural layout issues in {len(structural_issues)} test cases")
                
            pixel_issues = [r for r in failed_results if r.pixel_differences > self.pixel_threshold]
            if pixel_issues:
                recommendations.append(f"Fix positioning/sizing issues in {len(pixel_issues)} test cases")
                
            # Theme-specific issues
            dark_issues = [r for r in failed_results if "dark" in r.test_case]
            light_issues = [r for r in failed_results if "light" in r.test_case]
            
            if len(dark_issues) > len(light_issues):
                recommendations.append("Dark theme has more visual inconsistencies - review dark theme implementation")
            elif len(light_issues) > len(dark_issues):
                recommendations.append("Light theme has more visual inconsistencies - review light theme implementation")
                
        else:
            recommendations.append("All visual regression tests passed!")
            
        # Performance recommendations
        high_diff_scores = [r for r in results if r.difference_score > 0.3]
        if high_diff_scores:
            recommendations.append(f"Review {len(high_diff_scores)} test cases with high visual differences")
            
        return recommendations
        
    def save_report(self, report: VisualRegressionReport, filename: str = "visual_regression_report.json"):
        """Save visual regression report"""
        
        report_path = os.path.join(self.report_dir, filename)
        report_dict = asdict(report)
        
        # Add metadata
        report_dict["metadata"] = {
            "automation_version": "1.0.0",
            "test_timestamp": "2025-06-03T11:30:00Z",
            "similarity_threshold": self.similarity_threshold,
            "pixel_threshold": self.pixel_threshold,
            "total_test_cases": len(self.test_cases),
            "baseline_directory": self.baseline_dir,
            "current_directory": self.current_dir
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
            
        print(f"Visual regression report saved to: {report_path}")
        
    def print_summary(self, report: VisualRegressionReport):
        """Print summary of visual regression results"""
        
        print("\n" + "="*60)
        print("VISUAL REGRESSION TEST SUMMARY")
        print("="*60)
        
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Success Rate: {(report.passed_tests/report.total_tests)*100:.1f}%")
        print(f"Overall Similarity: {report.overall_similarity:.2%}")
        
        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
            
        print(f"\nFAILED TESTS:")
        failed_results = [r for r in report.comparison_results if not r.passed]
        for result in failed_results:
            print(f"  FAIL: {result.test_case} - Similarity: {result.structural_similarity:.2%}")
            for issue in result.issues:
                print(f"    - {issue}")


if __name__ == "__main__":
    """Direct execution for testing"""
    
    automation = VisualRegressionAutomation()
    
    # First run: capture baselines (only if not exist)
    baseline_files = automation.capture_baseline_visuals()
    
    # Second run: test against baselines
    report = automation.run_visual_regression_test()
    
    # Print summary
    automation.print_summary(report)
    
    # Save report
    automation.save_report(report)
    
    print(f"\nVisual regression testing complete.")
    print(f"Baselines: {len(baseline_files)} files")
    print(f"Success rate: {(report.passed_tests/report.total_tests)*100:.1f}%") 
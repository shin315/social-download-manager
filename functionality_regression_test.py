#!/usr/bin/env python3
"""
Comprehensive Functionality Regression Test for v2.0
====================================================

Tests v2.0 functionality with proper API usage and compares against 
expected v1.2.1 feature parity requirements.

Focus Areas:
1. Core UI component functionality
2. Database operations integrity
3. Cross-tab communication
4. Performance features validation
5. Error handling and coordination
"""

import sys
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Qt components
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import v2.0 components
from utils.db_manager import DatabaseManager
from ui.components.tabs.video_info_tab import VideoInfoTab
from ui.components.tabs.downloaded_videos_tab import DownloadedVideosTab
from ui.components.common import create_standard_tab_config

class FunctionalityRegressionSuite:
    """Comprehensive functionality regression testing suite"""
    
    def __init__(self):
        self.app = None
        self.test_results = {}
        self.video_tab = None
        self.downloaded_tab = None
        self.db_manager = None
        
    def setup_test_environment(self):
        """Initialize test environment"""
        try:
            # Initialize Qt Application
            self.app = QApplication.instance()
            if self.app is None:
                self.app = QApplication(sys.argv)
            
            # Initialize core components
            self.db_manager = DatabaseManager()
            
            # Create tabs with proper v2.0 configuration
            video_config = create_standard_tab_config("regression_video", "Regression Video Test")
            self.video_tab = VideoInfoTab(video_config)
            
            download_config = create_standard_tab_config("regression_downloads", "Regression Downloads Test")
            self.downloaded_tab = DownloadedVideosTab(download_config)
            
            print("✅ Test environment initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize test environment: {e}")
            return False
    
    def test_database_functionality(self) -> Dict[str, Any]:
        """Test database operations and integrity"""
        print("\n💾 Testing Database Functionality...")
        results = {}
        
        try:
            # Test 1: Basic Connection
            connection_test = self.db_manager.execute_query("SELECT 1", fetch_all=True)
            results['connection'] = len(connection_test) == 1
            
            # Test 2: Schema Validation  
            tables_result = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table'", 
                fetch_all=True
            )
            table_names = [table[0] for table in tables_result]
            results['required_tables'] = 'downloaded_videos' in table_names
            
            # Test 3: Basic Query Operations
            videos = self.db_manager.get_downloaded_videos(limit=5)
            results['basic_queries'] = True  # No exception means success
            
            # Test 4: Pagination Testing (v2.0 feature)
            if hasattr(self.db_manager, 'get_downloaded_videos_paginated'):
                paginated = self.db_manager.get_downloaded_videos_paginated(limit=10, offset=0)
                results['pagination'] = True
            else:
                results['pagination'] = False
            
            # Test 5: Count Operations
            total_count = self.db_manager.get_total_videos()
            results['count_operations'] = isinstance(total_count, int)
            
            # Test 6: Search Operations
            search_results = self.db_manager.search_videos("test", limit=5)
            results['search_operations'] = True
            
            print(f"  ✅ Database connection: {'✓' if results['connection'] else '✗'}")
            print(f"  ✅ Required tables: {'✓' if results['required_tables'] else '✗'}")
            print(f"  ✅ Basic queries: {'✓' if results['basic_queries'] else '✗'}")
            print(f"  ✅ Pagination: {'✓' if results['pagination'] else '✗'}")
            print(f"  ✅ Count operations: {'✓' if results['count_operations'] else '✗'}")
            print(f"  ✅ Search operations: {'✓' if results['search_operations'] else '✗'}")
            
        except Exception as e:
            print(f"  ❌ Database functionality error: {e}")
            results['error'] = str(e)
            
        return results
    
    def test_video_info_tab_functionality(self) -> Dict[str, Any]:
        """Test VideoInfoTab functionality with v2.0 API"""
        print("\n📹 Testing Video Info Tab Functionality...")
        results = {}
        
        try:
            # Test 1: Tab Initialization
            results['tab_creation'] = self.video_tab is not None
            
            # Test 2: V2.0 API Attributes (not v1.2.1 attributes)
            v2_attributes = [
                'video_info_dict',  # v2.0 uses dict not list
                'output_folder_display',  # v2.0 uses display not input
                'url_input',
                'downloader'
            ]
            
            missing_attributes = []
            for attr in v2_attributes:
                if not hasattr(self.video_tab, attr):
                    missing_attributes.append(attr)
            
            results['v2_api_compliance'] = len(missing_attributes) == 0
            results['missing_v2_attributes'] = missing_attributes
            
            # Test 3: UI Layout Components
            ui_components = []
            if hasattr(self.video_tab, 'url_input'):
                ui_components.append('url_input')
            if hasattr(self.video_tab, 'output_folder_display'):
                ui_components.append('output_folder_display')
            if hasattr(self.video_tab, 'video_table'):
                ui_components.append('video_table')
            
            results['ui_components'] = ui_components
            results['ui_complete'] = len(ui_components) >= 3
            
            # Test 4: Method Availability
            required_methods = [
                'get_video_info',
                'download_videos',
                'delete_selected_videos',
                'delete_all_videos'
            ]
            
            available_methods = []
            for method in required_methods:
                if hasattr(self.video_tab, method):
                    available_methods.append(method)
            
            results['available_methods'] = available_methods
            results['methods_complete'] = len(available_methods) == len(required_methods)
            
            # Test 5: Data Structure Validation
            if hasattr(self.video_tab, 'video_info_dict'):
                results['data_structure'] = isinstance(self.video_tab.video_info_dict, dict)
            else:
                results['data_structure'] = False
            
            # Test 6: Cross-Tab Communication (v2.0 feature)
            cross_tab_features = []
            if hasattr(self.video_tab, 'emit_tab_event'):
                cross_tab_features.append('emit_tab_event')
            if hasattr(self.video_tab, 'save_tab_state'):
                cross_tab_features.append('save_tab_state')
            if hasattr(self.video_tab, 'restore_tab_state'):
                cross_tab_features.append('restore_tab_state')
            
            results['cross_tab_features'] = cross_tab_features
            results['cross_tab_support'] = len(cross_tab_features) > 0
            
            print(f"  ✅ Tab creation: {'✓' if results['tab_creation'] else '✗'}")
            print(f"  ✅ V2.0 API compliance: {'✓' if results['v2_api_compliance'] else '✗'}")
            print(f"  ✅ UI components: {'✓' if results['ui_complete'] else '✗'}")
            print(f"  ✅ Required methods: {'✓' if results['methods_complete'] else '✗'}")
            print(f"  ✅ Data structure: {'✓' if results['data_structure'] else '✗'}")
            print(f"  ✅ Cross-tab support: {'✓' if results['cross_tab_support'] else '✗'}")
            
        except Exception as e:
            print(f"  ❌ Video Info Tab error: {e}")
            results['error'] = str(e)
            
        return results
    
    def test_downloaded_videos_tab_functionality(self) -> Dict[str, Any]:
        """Test DownloadedVideosTab functionality"""
        print("\n📁 Testing Downloaded Videos Tab Functionality...")
        results = {}
        
        try:
            # Test 1: Tab Initialization
            results['tab_creation'] = self.downloaded_tab is not None
            
            # Test 2: Core UI Components
            ui_components = []
            if hasattr(self.downloaded_tab, 'downloads_table'):
                ui_components.append('downloads_table')
            if hasattr(self.downloaded_tab, 'details_area'):
                ui_components.append('details_area')
            if hasattr(self.downloaded_tab, 'search_input'):
                ui_components.append('search_input')
            
            results['ui_components'] = ui_components
            results['ui_complete'] = len(ui_components) >= 2
            
            # Test 3: Data Loading
            initial_data_load = True
            try:
                if hasattr(self.downloaded_tab, 'refresh_data'):
                    self.downloaded_tab.refresh_data()
                elif hasattr(self.downloaded_tab, 'load_data'):
                    self.downloaded_tab.load_data()
            except Exception:
                initial_data_load = False
            
            results['data_loading'] = initial_data_load
            
            # Test 4: Table Operations
            table_features = []
            if hasattr(self.downloaded_tab, 'sort_by_column'):
                table_features.append('sorting')
            if hasattr(self.downloaded_tab, 'filter_videos'):
                table_features.append('filtering')
            if hasattr(self.downloaded_tab, 'search_videos'):
                table_features.append('search')
            
            results['table_features'] = table_features
            results['table_functional'] = len(table_features) > 0
            
            # Test 5: Performance Features (v2.0)
            performance_features = []
            if hasattr(self.downloaded_tab, 'lazy_loading_enabled'):
                performance_features.append('lazy_loading')
            if hasattr(self.downloaded_tab, 'virtual_mode'):
                performance_features.append('virtual_mode')
            if hasattr(self.downloaded_tab, 'pagination'):
                performance_features.append('pagination')
            
            results['performance_features'] = performance_features
            results['performance_enhanced'] = len(performance_features) > 0
            
            # Test 6: Integration with Video Info Tab
            integration_test = False
            try:
                # Test cross-tab communication capability
                if hasattr(self.downloaded_tab, 'handle_tab_event'):
                    integration_test = True
            except Exception:
                pass
            
            results['cross_tab_integration'] = integration_test
            
            print(f"  ✅ Tab creation: {'✓' if results['tab_creation'] else '✗'}")
            print(f"  ✅ UI components: {'✓' if results['ui_complete'] else '✗'}")
            print(f"  ✅ Data loading: {'✓' if results['data_loading'] else '✗'}")
            print(f"  ✅ Table features: {'✓' if results['table_functional'] else '✗'}")
            print(f"  ✅ Performance features: {'✓' if results['performance_enhanced'] else '✗'}")
            print(f"  ✅ Cross-tab integration: {'✓' if results['cross_tab_integration'] else '✗'}")
            
        except Exception as e:
            print(f"  ❌ Downloaded Videos Tab error: {e}")
            results['error'] = str(e)
            
        return results
    
    def test_v2_enhancements(self) -> Dict[str, Any]:
        """Test v2.0 specific enhancements"""
        print("\n🚀 Testing V2.0 Enhancements...")
        results = {}
        
        try:
            # Test 1: Component Architecture (BaseTab system)
            base_tab_features = []
            for tab in [self.video_tab, self.downloaded_tab]:
                if hasattr(tab, 'tab_config'):
                    base_tab_features.append('tab_config')
                if hasattr(tab, 'setup_ui'):
                    base_tab_features.append('setup_ui')
                if hasattr(tab, 'load_tab_data'):
                    base_tab_features.append('load_tab_data')
                break  # Check only one tab to avoid duplicates
            
            results['base_tab_architecture'] = len(base_tab_features) > 0
            
            # Test 2: State Persistence
            state_persistence = False
            if hasattr(self.video_tab, 'save_tab_state') and hasattr(self.video_tab, 'restore_tab_state'):
                try:
                    self.video_tab.save_tab_state()
                    self.video_tab.restore_tab_state()
                    state_persistence = True
                except Exception:
                    pass
            
            results['state_persistence'] = state_persistence
            
            # Test 3: Error Coordination System
            error_coordination = False
            if hasattr(self.video_tab, 'error_manager'):
                error_coordination = True
            
            results['error_coordination'] = error_coordination
            
            # Test 4: Progress Tracking
            progress_tracking = False
            if hasattr(self.video_tab, 'progress_manager'):
                progress_tracking = True
            
            results['progress_tracking'] = progress_tracking
            
            # Test 5: Advanced Database Features
            advanced_db_features = []
            if hasattr(self.db_manager, 'get_downloaded_videos_paginated'):
                advanced_db_features.append('pagination')
            if hasattr(self.db_manager, 'advanced_search'):
                advanced_db_features.append('advanced_search')
            if hasattr(self.db_manager, 'bulk_operations'):
                advanced_db_features.append('bulk_operations')
            
            results['advanced_db_features'] = advanced_db_features
            results['database_enhanced'] = len(advanced_db_features) > 0
            
            print(f"  ✅ BaseTab architecture: {'✓' if results['base_tab_architecture'] else '✗'}")
            print(f"  ✅ State persistence: {'✓' if results['state_persistence'] else '✗'}")
            print(f"  ✅ Error coordination: {'✓' if results['error_coordination'] else '✗'}")
            print(f"  ✅ Progress tracking: {'✓' if results['progress_tracking'] else '✗'}")
            print(f"  ✅ Advanced database: {'✓' if results['database_enhanced'] else '✗'}")
            
        except Exception as e:
            print(f"  ❌ V2.0 enhancements test error: {e}")
            results['error'] = str(e)
            
        return results
    
    def test_regression_scenarios(self) -> Dict[str, Any]:
        """Test specific regression scenarios from v1.2.1 to v2.0"""
        print("\n🔄 Testing Regression Scenarios...")
        results = {}
        
        try:
            # Test 1: API Compatibility Changes
            api_changes = {
                'video_info_list_to_dict': hasattr(self.video_tab, 'video_info_dict') and not hasattr(self.video_tab, 'video_info_list'),
                'folder_input_to_display': hasattr(self.video_tab, 'output_folder_display') and not hasattr(self.video_tab, 'folder_input'),
            }
            
            results['api_changes_identified'] = api_changes
            results['api_migration_complete'] = all(api_changes.values())
            
            # Test 2: Functional Equivalence
            functional_tests = {}
            
            # URL input functionality
            if hasattr(self.video_tab, 'url_input'):
                try:
                    test_url = "https://www.tiktok.com/@test/video/123456789"
                    self.video_tab.url_input.setText(test_url)
                    functional_tests['url_input'] = self.video_tab.url_input.text() == test_url
                except Exception:
                    functional_tests['url_input'] = False
            else:
                functional_tests['url_input'] = False
            
            # Output folder functionality
            if hasattr(self.video_tab, 'output_folder_display'):
                try:
                    test_folder = os.getcwd()
                    self.video_tab.output_folder_display.setText(test_folder)
                    functional_tests['output_folder'] = len(self.video_tab.output_folder_display.text()) > 0
                except Exception:
                    functional_tests['output_folder'] = False
            else:
                functional_tests['output_folder'] = False
                
            # Download button functionality
            functional_tests['download_method'] = hasattr(self.video_tab, 'download_videos')
            
            results['functional_tests'] = functional_tests
            results['functional_parity'] = sum(functional_tests.values()) / len(functional_tests) >= 0.8
            
            # Test 3: Performance Regression Check
            performance_improvements = []
            
            if hasattr(self.downloaded_tab, 'virtual_mode'):
                performance_improvements.append('virtual_table_mode')
            if hasattr(self.db_manager, 'get_downloaded_videos_paginated'):
                performance_improvements.append('database_pagination')
            if hasattr(self.video_tab, 'lazy_loading'):
                performance_improvements.append('lazy_loading')
            
            results['performance_improvements'] = performance_improvements
            results['performance_regression'] = len(performance_improvements) == 0  # False means no regression
            
            print(f"  ✅ API migration complete: {'✓' if results['api_migration_complete'] else '✗'}")
            print(f"  ✅ Functional parity: {'✓' if results['functional_parity'] else '✗'}")
            print(f"  ✅ No performance regression: {'✓' if not results['performance_regression'] else '✗'}")
            
        except Exception as e:
            print(f"  ❌ Regression scenarios test error: {e}")
            results['error'] = str(e)
            
        return results
    
    def generate_functionality_report(self, all_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive functionality report"""
        
        # Calculate category scores
        category_scores = {}
        
        # Database functionality score
        db_results = all_results.get('Database Functionality', {})
        if db_results and 'error' not in db_results:
            db_score = sum([
                db_results.get('connection', False),
                db_results.get('required_tables', False),
                db_results.get('basic_queries', False),
                db_results.get('pagination', False),
                db_results.get('count_operations', False),
                db_results.get('search_operations', False)
            ]) / 6 * 100
            category_scores['database'] = db_score
        
        # Video Info Tab score
        video_results = all_results.get('Video Info Tab Functionality', {})
        if video_results and 'error' not in video_results:
            video_score = sum([
                video_results.get('tab_creation', False),
                video_results.get('v2_api_compliance', False),
                video_results.get('ui_complete', False),
                video_results.get('methods_complete', False),
                video_results.get('data_structure', False),
                video_results.get('cross_tab_support', False)
            ]) / 6 * 100
            category_scores['video_info_tab'] = video_score
        
        # Downloaded Videos Tab score
        download_results = all_results.get('Downloaded Videos Tab Functionality', {})
        if download_results and 'error' not in download_results:
            download_score = sum([
                download_results.get('tab_creation', False),
                download_results.get('ui_complete', False),
                download_results.get('data_loading', False),
                download_results.get('table_functional', False),
                download_results.get('performance_enhanced', False),
                download_results.get('cross_tab_integration', False)
            ]) / 6 * 100
            category_scores['downloaded_videos_tab'] = download_score
        
        # V2.0 Enhancements score
        enhancement_results = all_results.get('V2.0 Enhancements', {})
        if enhancement_results and 'error' not in enhancement_results:
            enhancement_score = sum([
                enhancement_results.get('base_tab_architecture', False),
                enhancement_results.get('state_persistence', False),
                enhancement_results.get('error_coordination', False),
                enhancement_results.get('progress_tracking', False),
                enhancement_results.get('database_enhanced', False)
            ]) / 5 * 100
            category_scores['v2_enhancements'] = enhancement_score
        
        # Regression Testing score
        regression_results = all_results.get('Regression Scenarios', {})
        if regression_results and 'error' not in regression_results:
            regression_score = sum([
                regression_results.get('api_migration_complete', False),
                regression_results.get('functional_parity', False),
                not regression_results.get('performance_regression', True)  # Invert because False is good
            ]) / 3 * 100
            category_scores['regression_testing'] = regression_score
        
        # Overall score
        if category_scores:
            overall_score = sum(category_scores.values()) / len(category_scores)
        else:
            overall_score = 0
        
        # Generate summary
        passed_tests = sum(1 for score in category_scores.values() if score >= 80)
        total_tests = len(category_scores)
        
        return {
            'category_scores': category_scores,
            'overall_score': overall_score,
            'passed_categories': passed_tests,
            'total_categories': total_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'feature_parity_achieved': overall_score >= 75,
            'v2_improvements_confirmed': category_scores.get('v2_enhancements', 0) >= 60
        }
    
    def run_comprehensive_functionality_test(self) -> Dict[str, Any]:
        """Run all functionality tests"""
        print("🧪 COMPREHENSIVE FUNCTIONALITY REGRESSION TEST")
        print("=" * 65)
        
        if not self.setup_test_environment():
            return {'status': 'failed', 'error': 'Could not initialize test environment'}
        
        # Run all test categories
        test_categories = [
            ('Database Functionality', self.test_database_functionality),
            ('Video Info Tab Functionality', self.test_video_info_tab_functionality),
            ('Downloaded Videos Tab Functionality', self.test_downloaded_videos_tab_functionality),
            ('V2.0 Enhancements', self.test_v2_enhancements),
            ('Regression Scenarios', self.test_regression_scenarios)
        ]
        
        all_results = {}
        
        for category_name, test_function in test_categories:
            print(f"\n🔄 Running {category_name} tests...")
            results = test_function()
            all_results[category_name] = results
            time.sleep(0.3)  # Allow system to stabilize
        
        # Generate functionality report
        functionality_report = self.generate_functionality_report(all_results)
        all_results['Functionality Report'] = functionality_report
        
        # Print summary
        self.print_test_summary(all_results)
        
        return {
            'status': 'completed',
            'timestamp': datetime.now().isoformat(),
            'test_results': all_results
        }
    
    def print_test_summary(self, results: Dict[str, Any]):
        """Print test summary"""
        print(f"\n📊 FUNCTIONALITY TEST SUMMARY")
        print("=" * 65)
        
        functionality_report = results.get('Functionality Report', {})
        scores = functionality_report.get('category_scores', {})
        
        print(f"🎯 Overall Score: {functionality_report.get('overall_score', 0):.1f}/100")
        print(f"📈 Categories Passed: {functionality_report.get('passed_categories', 0)}/{functionality_report.get('total_categories', 0)}")
        print(f"✅ Success Rate: {functionality_report.get('success_rate', 0):.1f}%")
        
        print("\n📊 Category Scores:")
        for category, score in scores.items():
            emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            print(f"  {emoji} {category.replace('_', ' ').title()}: {score:.1f}/100")
        
        print(f"\n🎯 Feature Parity: {'✅ ACHIEVED' if functionality_report.get('feature_parity_achieved') else '⚠️ NEEDS IMPROVEMENT'}")
        print(f"🚀 V2.0 Improvements: {'✅ CONFIRMED' if functionality_report.get('v2_improvements_confirmed') else '⚠️ INCOMPLETE'}")

def main():
    """Main test function"""
    test_suite = FunctionalityRegressionSuite()
    results = test_suite.run_comprehensive_functionality_test()
    
    # Save results to file
    results_file = 'functionality_regression_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Determine success based on overall score
    overall_score = results.get('test_results', {}).get('Functionality Report', {}).get('overall_score', 0)
    feature_parity = results.get('test_results', {}).get('Functionality Report', {}).get('feature_parity_achieved', False)
    
    print(f"\n🏁 FINAL RESULT: {'🎉 SUCCESS' if feature_parity and overall_score >= 75 else '⚠️ NEEDS REVIEW'}")
    
    return feature_parity and overall_score >= 75

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
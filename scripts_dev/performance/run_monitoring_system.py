#!/usr/bin/env python3
"""
Performance Monitoring System Test Runner
========================================

Comprehensive testing suite for Social Download Manager v2.0 performance monitoring system.
Tests real-time metrics collection, dashboard functionality, alert system, database operations,
and reporting capabilities.

Usage:
    python run_monitoring_system.py [--mode=MODE] [--duration=SECONDS]

Modes:
    all         - Run all monitoring tests (default)
    metrics     - Test metrics collection only
    dashboard   - Test dashboard functionality only
    alerts      - Test alert system only
    database    - Test database operations only
    reports     - Test reporting capabilities only
    demo        - Run interactive demonstration
"""

import os
import sys
import time
import asyncio
import argparse
from typing import Dict, List, Any
import tempfile
import shutil

# Add scripts directory to path for imports
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts', 'performance')
sys.path.insert(0, scripts_dir)

try:
    from monitoring_system import (
        PerformanceMonitoringSystem, MetricsCollector, AlertManager, 
        PerformanceDashboard, MetricsDatabase, SystemMetrics, DownloadMetrics,
        UIMetrics, AlertConfig, PerformanceAlert
    )
except ImportError as e:
    print(f"❌ Error importing monitoring system: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install psutil")
    sys.exit(1)

class MonitoringTestRunner:
    """Comprehensive monitoring system test runner."""
    
    def __init__(self, duration: float = 30.0):
        self.duration = duration
        self.results = {}
        self.temp_db_path = None
        
    async def test_metrics_collection(self) -> Dict[str, Any]:
        """Test real-time metrics collection."""
        print("\n📊 Phase 1: Metrics Collection Testing")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            collector = MetricsCollector(collection_interval=0.5)
            collected_metrics = []
            
            def collect_callback(metrics: SystemMetrics):
                collected_metrics.append(metrics)
            
            collector.add_callback(collect_callback)
            
            print(f"  Starting metrics collection for 5 seconds...")
            collector.start()
            
            await asyncio.sleep(5)
            
            collector.stop()
            
            if len(collected_metrics) >= 8:  # Should have ~10 metrics at 0.5s intervals
                print(f"✅ Collected {len(collected_metrics)} metric snapshots")
                
                # Validate metrics content
                latest = collected_metrics[-1]
                print(f"  Latest metrics:")
                print(f"    CPU: {latest.cpu_percent:.1f}%")
                print(f"    Memory: {latest.memory_usage_mb:.1f} MB ({latest.memory_percent:.1f}%)")
                print(f"    Disk: {latest.disk_usage_gb:.1f} GB ({latest.disk_percent:.1f}%)")
                print(f"    Threads: {latest.active_threads}")
                
                results["details"]["metrics_collected"] = len(collected_metrics)
                results["details"]["collection_rate"] = len(collected_metrics) / 5.0
                results["details"]["cpu_range"] = [min(m.cpu_percent for m in collected_metrics),
                                                  max(m.cpu_percent for m in collected_metrics)]
                results["details"]["memory_range_mb"] = [min(m.memory_usage_mb for m in collected_metrics),
                                                        max(m.memory_usage_mb for m in collected_metrics)]
                
                # Validate ranges are reasonable
                if latest.cpu_percent < 0 or latest.cpu_percent > 100:
                    results["errors"].append(f"Invalid CPU percentage: {latest.cpu_percent}")
                
                if latest.memory_percent < 0 or latest.memory_percent > 100:
                    results["errors"].append(f"Invalid memory percentage: {latest.memory_percent}")
                
            else:
                results["status"] = "FAILED"
                results["errors"].append(f"Insufficient metrics collected: {len(collected_metrics)}")
            
            print(f"✅ Metrics collection tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Metrics collection failed: {e}")
        
        return results
    
    async def test_dashboard_functionality(self) -> Dict[str, Any]:
        """Test dashboard functionality and data formatting."""
        print("\n📈 Phase 2: Dashboard Functionality")
        print("-" * 35)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            dashboard = PerformanceDashboard(update_interval=1.0)
            
            # Add sample system metrics
            print(f"  Adding sample system metrics...")
            for i in range(10):
                metrics = SystemMetrics(
                    timestamp=time.time() - (10 - i),
                    cpu_percent=15.0 + i * 2.5,
                    memory_usage_mb=1024.0 + i * 50,
                    memory_percent=40.0 + i,
                    disk_usage_gb=50.0 + i,
                    disk_percent=25.0 + i,
                    network_sent_mb=100.0 + i * 5,
                    network_recv_mb=80.0 + i * 3,
                    active_threads=12 + i,
                    gc_collections=50 + i * 2
                )
                dashboard.add_system_metrics(metrics)
            
            # Add sample download metrics
            print(f"  Adding sample download metrics...")
            for i in range(5):
                download_metrics = DownloadMetrics(
                    timestamp=time.time() - (5 - i),
                    download_id=f"test_download_{i}",
                    url=f"https://test.com/video{i}.mp4",
                    platform="TikTok" if i % 2 == 0 else "YouTube",
                    file_size_mb=20.0 + i * 10,
                    download_speed_mbps=3.0 + i * 0.5,
                    time_elapsed=25.0 + i * 5,
                    status="completed",
                    progress_percent=100.0
                )
                dashboard.add_download_metrics(download_metrics)
            
            # Add sample UI metrics
            print(f"  Adding sample UI metrics...")
            for action in ["table_load", "search", "filter", "scroll", "click"]:
                ui_metrics = UIMetrics(
                    timestamp=time.time(),
                    action=action,
                    response_time_ms=100.0 + len(action) * 20,
                    ui_thread_blocked=False,
                    memory_usage_mb=45.0,
                    fps=60.0,
                    items_rendered=100
                )
                dashboard.add_ui_metrics(ui_metrics)
            
            # Test dashboard status
            print(f"  Testing dashboard status generation...")
            status = dashboard.get_current_status()
            
            if status.get("status") == "no_data":
                results["errors"].append("Dashboard shows no data despite adding metrics")
            else:
                print(f"    System CPU: {status['system']['cpu_percent']:.1f}%")
                print(f"    Downloads completed: {status['downloads']['completed_count']}")
                print(f"    UI avg response: {status['ui']['avg_response_time_ms']:.1f}ms")
                
                results["details"]["dashboard_status"] = {
                    "cpu_percent": status['system']['cpu_percent'],
                    "memory_percent": status['system']['memory_percent'],
                    "downloads_completed": status['downloads']['completed_count'],
                    "ui_avg_response": status['ui']['avg_response_time_ms']
                }
            
            # Test data export formats
            print(f"  Testing data export formats...")
            
            # JSON export
            json_data = dashboard.export_dashboard_data("json")
            if json_data and len(json_data) > 100:
                print(f"    JSON export: {len(json_data)} characters")
                results["details"]["json_export_size"] = len(json_data)
            else:
                results["errors"].append("JSON export failed or too small")
            
            # Text export
            text_data = dashboard.export_dashboard_data("text")
            if text_data and "Performance Dashboard" in text_data:
                print(f"    Text export: {len(text_data)} characters")
                results["details"]["text_export_size"] = len(text_data)
            else:
                results["errors"].append("Text export failed or missing header")
            
            print(f"✅ Dashboard functionality tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Dashboard functionality failed: {e}")
        
        return results
    
    async def test_alert_system(self) -> Dict[str, Any]:
        """Test alert management and threshold monitoring."""
        print("\n🚨 Phase 3: Alert System Testing")
        print("-" * 35)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            alert_manager = AlertManager()
            triggered_alerts = []
            
            def alert_callback(alert: PerformanceAlert):
                triggered_alerts.append(alert)
            
            alert_manager.add_callback(alert_callback)
            
            print(f"  Testing alert configurations...")
            
            # Test default alerts exist
            default_alerts = list(alert_manager.alert_configs.keys())
            print(f"    Default alerts: {len(default_alerts)} configured")
            expected_alerts = ["cpu_percent", "memory_percent", "disk_percent", 
                             "download_speed_mbps", "ui_response_time_ms"]
            
            for expected in expected_alerts:
                if expected not in default_alerts:
                    results["errors"].append(f"Missing default alert: {expected}")
            
            # Test alert triggering
            print(f"  Testing alert triggering...")
            
            # Trigger CPU alert (threshold 90%, send 95%)
            alert_manager.check_metric("cpu_percent", 95.0)
            
            # Trigger memory alert (threshold 85%, send 90%)
            alert_manager.check_metric("memory_percent", 90.0)
            
            # Test low download speed alert (threshold 0.1 MB/s, send 0.05 MB/s)
            alert_manager.check_metric("download_speed_mbps", 0.05)
            
            await asyncio.sleep(1)  # Allow processing
            
            print(f"    Triggered alerts: {len(triggered_alerts)}")
            
            if len(triggered_alerts) >= 3:
                for alert in triggered_alerts:
                    print(f"      - {alert.severity.upper()}: {alert.message}")
                
                results["details"]["alerts_triggered"] = len(triggered_alerts)
                results["details"]["alert_types"] = [alert.metric_name for alert in triggered_alerts]
                
                # Validate alert content
                for alert in triggered_alerts:
                    if alert.current_value <= alert.threshold_value and alert.metric_name != "download_speed_mbps":
                        results["errors"].append(f"Alert logic error for {alert.metric_name}")
            else:
                results["errors"].append(f"Expected at least 3 alerts, got {len(triggered_alerts)}")
            
            # Test alert resolution
            print(f"  Testing alert resolution...")
            active_before = len(alert_manager.get_active_alerts())
            
            # Send normal values to resolve alerts
            alert_manager.check_metric("cpu_percent", 30.0)
            alert_manager.check_metric("memory_percent", 50.0)
            alert_manager.check_metric("download_speed_mbps", 5.0)
            
            active_after = len(alert_manager.get_active_alerts())
            print(f"    Active alerts: {active_before} → {active_after}")
            
            results["details"]["alert_resolution"] = {
                "before": active_before,
                "after": active_after
            }
            
            # Test cooldown functionality
            print(f"  Testing alert cooldown...")
            
            # Add custom alert with short cooldown
            short_cooldown_alert = AlertConfig("test_metric", 50.0, "gt", True, 2, "info")
            alert_manager.add_alert_config(short_cooldown_alert)
            
            # Trigger it twice rapidly
            alert_manager.check_metric("test_metric", 75.0)
            initial_count = len(triggered_alerts)
            
            alert_manager.check_metric("test_metric", 80.0)  # Should be ignored due to cooldown
            cooldown_count = len(triggered_alerts)
            
            if cooldown_count == initial_count + 1:
                print(f"    Cooldown working: second alert ignored")
                results["details"]["cooldown_working"] = True
            else:
                results["errors"].append("Cooldown not working properly")
            
            print(f"✅ Alert system tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Alert system failed: {e}")
        
        return results
    
    async def test_database_operations(self) -> Dict[str, Any]:
        """Test database storage and retrieval operations."""
        print("\n💾 Phase 4: Database Operations")
        print("-" * 30)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Create temporary database
            temp_dir = tempfile.mkdtemp()
            self.temp_db_path = os.path.join(temp_dir, "test_metrics.db")
            
            db = MetricsDatabase(self.temp_db_path)
            
            print(f"  Testing database creation...")
            if os.path.exists(self.temp_db_path):
                print(f"    Database created: {self.temp_db_path}")
                results["details"]["database_created"] = True
            else:
                results["errors"].append("Database file not created")
            
            # Test system metrics storage
            print(f"  Testing system metrics storage...")
            system_metrics = []
            for i in range(10):
                metrics = SystemMetrics(
                    timestamp=time.time() - (10 - i) * 60,  # 1 minute intervals
                    cpu_percent=20.0 + i * 5,
                    memory_usage_mb=1000.0 + i * 100,
                    memory_percent=30.0 + i * 2,
                    disk_usage_gb=40.0 + i,
                    disk_percent=20.0 + i,
                    network_sent_mb=50.0 + i * 10,
                    network_recv_mb=30.0 + i * 5,
                    active_threads=10 + i,
                    gc_collections=20 + i * 3
                )
                system_metrics.append(metrics)
                db.store_system_metrics(metrics)
            
            print(f"    Stored {len(system_metrics)} system metrics")
            
            # Test download metrics storage
            print(f"  Testing download metrics storage...")
            download_metrics = []
            for i in range(5):
                metrics = DownloadMetrics(
                    timestamp=time.time() - (5 - i) * 30,
                    download_id=f"download_{i}",
                    url=f"https://test.com/video{i}.mp4",
                    platform="TikTok" if i % 2 == 0 else "YouTube",
                    file_size_mb=15.0 + i * 5,
                    download_speed_mbps=2.0 + i * 0.3,
                    time_elapsed=20.0 + i * 3,
                    status="completed" if i < 4 else "failed",
                    progress_percent=100.0 if i < 4 else 75.0,
                    error_message=None if i < 4 else "Network timeout"
                )
                download_metrics.append(metrics)
                db.store_download_metrics(metrics)
            
            print(f"    Stored {len(download_metrics)} download metrics")
            
            # Test UI metrics storage
            print(f"  Testing UI metrics storage...")
            ui_metrics = []
            for action in ["load", "search", "filter", "scroll"]:
                metrics = UIMetrics(
                    timestamp=time.time(),
                    action=action,
                    response_time_ms=100.0 + len(action) * 25,
                    ui_thread_blocked=action == "load",  # Only load blocks UI
                    memory_usage_mb=40.0 + len(action),
                    fps=60.0 if action != "load" else 30.0,
                    items_rendered=50 + len(action) * 10
                )
                ui_metrics.append(metrics)
                db.store_ui_metrics(metrics)
            
            print(f"    Stored {len(ui_metrics)} UI metrics")
            
            # Test data retrieval
            print(f"  Testing data retrieval...")
            
            # Test system metrics range query
            start_time = time.time() - 700  # 11+ minutes ago
            end_time = time.time()
            retrieved_metrics = db.get_system_metrics_range(start_time, end_time)
            
            print(f"    Retrieved {len(retrieved_metrics)} system metrics")
            if len(retrieved_metrics) == len(system_metrics):
                results["details"]["system_metrics_retrieval"] = True
            else:
                results["errors"].append(f"System metrics retrieval mismatch: {len(retrieved_metrics)} vs {len(system_metrics)}")
            
            # Test download summary
            download_summary = db.get_download_summary(hours=1)
            print(f"    Download summary:")
            print(f"      Total downloads: {download_summary.get('total_downloads', 0)}")
            print(f"      Success rate: {download_summary.get('success_rate', 0):.1f}%")
            print(f"      Average speed: {download_summary.get('avg_speed_mbps', 0):.2f} MB/s")
            
            if download_summary.get('total_downloads', 0) == len(download_metrics):
                results["details"]["download_summary"] = download_summary
            else:
                results["errors"].append("Download summary count mismatch")
            
            # Test alert storage
            print(f"  Testing alert storage...")
            test_alert = PerformanceAlert(
                timestamp=time.time(),
                metric_name="test_metric",
                current_value=95.0,
                threshold_value=90.0,
                severity="warning",
                message="Test alert for database storage"
            )
            db.store_alert(test_alert)
            
            results["details"]["database_operations"] = {
                "system_metrics_stored": len(system_metrics),
                "download_metrics_stored": len(download_metrics),
                "ui_metrics_stored": len(ui_metrics),
                "alerts_stored": 1
            }
            
            print(f"✅ Database operations tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Database operations failed: {e}")
        
        return results
    
    async def test_reporting_capabilities(self) -> Dict[str, Any]:
        """Test comprehensive reporting functionality."""
        print("\n📋 Phase 5: Reporting Capabilities")
        print("-" * 35)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Use temporary database if available
            db_path = self.temp_db_path or "data/database/test_performance_metrics.db"
            monitoring = PerformanceMonitoringSystem(db_path)
            
            print(f"  Testing performance summary generation...")
            
            # Add some test data
            for i in range(3):
                download_metrics = DownloadMetrics(
                    timestamp=time.time() - (3 - i) * 60,
                    download_id=f"report_test_{i}",
                    url=f"https://test.com/report{i}.mp4",
                    platform="YouTube",
                    file_size_mb=30.0 + i * 5,
                    download_speed_mbps=4.0 + i * 0.2,
                    time_elapsed=35.0 + i * 2,
                    status="completed",
                    progress_percent=100.0
                )
                monitoring.record_download_metrics(download_metrics)
            
            # Test performance summary
            summary = monitoring.get_performance_summary(hours=1)
            print(f"    Summary generated for last 1 hour")
            
            if "dashboard" in summary and "downloads" in summary and "alerts" in summary:
                print(f"      Downloads: {summary['downloads'].get('total_downloads', 0)}")
                print(f"      Active alerts: {summary['alerts']['active_count']}")
                
                results["details"]["summary_sections"] = list(summary.keys())
                results["details"]["downloads_in_summary"] = summary['downloads'].get('total_downloads', 0)
            else:
                results["errors"].append("Summary missing required sections")
            
            # Test JSON report export
            print(f"  Testing JSON report export...")
            json_report = monitoring.export_performance_report("json", hours=1)
            
            if json_report and len(json_report) > 200:
                print(f"    JSON report: {len(json_report)} characters")
                results["details"]["json_report_size"] = len(json_report)
                
                # Validate JSON structure
                import json
                try:
                    parsed = json.loads(json_report)
                    if "summary_period_hours" in parsed and "generated_at" in parsed:
                        results["details"]["json_structure_valid"] = True
                    else:
                        results["errors"].append("JSON report missing required fields")
                except json.JSONDecodeError:
                    results["errors"].append("JSON report is not valid JSON")
            else:
                results["errors"].append("JSON report too small or empty")
            
            # Test text report export
            print(f"  Testing text report export...")
            text_report = monitoring.export_performance_report("text", hours=1)
            
            if text_report and "PERFORMANCE REPORT" in text_report:
                print(f"    Text report: {len(text_report)} characters")
                results["details"]["text_report_size"] = len(text_report)
                
                # Check for required sections
                required_sections = ["DOWNLOAD PERFORMANCE", "ALERT SUMMARY", "SYSTEM STATUS"]
                found_sections = [section for section in required_sections if section in text_report]
                
                if len(found_sections) == len(required_sections):
                    results["details"]["text_report_sections"] = found_sections
                else:
                    results["errors"].append(f"Text report missing sections: {set(required_sections) - set(found_sections)}")
            else:
                results["errors"].append("Text report missing or no header")
            
            # Test report formats
            print(f"  Testing unsupported format handling...")
            try:
                monitoring.export_performance_report("xml", hours=1)
                results["errors"].append("Should have failed with unsupported format")
            except ValueError:
                print(f"    Correctly rejected unsupported format")
                results["details"]["format_validation"] = True
            
            print(f"✅ Reporting capabilities tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Reporting capabilities failed: {e}")
        
        return results
    
    async def test_integrated_monitoring(self) -> Dict[str, Any]:
        """Test integrated monitoring system functionality."""
        print("\n🔄 Phase 6: Integrated Monitoring Test")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Use temporary database if available
            db_path = self.temp_db_path or "data/database/integrated_test_metrics.db"
            monitoring = PerformanceMonitoringSystem(db_path)
            
            collected_alerts = []
            
            # Override alert callback to capture alerts
            original_on_alert = monitoring._on_alert
            def capture_alert(alert):
                collected_alerts.append(alert)
                # Still call original to test logging
                original_on_alert(alert)
            
            monitoring._on_alert = capture_alert
            
            print(f"  Starting integrated monitoring for 8 seconds...")
            monitoring.start()
            
            await asyncio.sleep(3)
            
            # Simulate download activity
            print(f"  Simulating download activity...")
            for i in range(2):
                download_metrics = DownloadMetrics(
                    timestamp=time.time(),
                    download_id=f"integrated_{i}",
                    url=f"https://test.com/integrated{i}.mp4",
                    platform="TikTok",
                    file_size_mb=40.0,
                    download_speed_mbps=6.0 - i * 2,  # Second download slower
                    time_elapsed=30.0,
                    status="downloading",
                    progress_percent=50.0 + i * 25
                )
                monitoring.record_download_metrics(download_metrics)
            
            # Simulate UI activity
            print(f"  Simulating UI activity...")
            for response_time in [200, 500, 1200]:  # Last one should trigger alert
                ui_metrics = UIMetrics(
                    timestamp=time.time(),
                    action="test_action",
                    response_time_ms=response_time,
                    ui_thread_blocked=response_time > 1000,
                    memory_usage_mb=50.0,
                    fps=60.0 if response_time < 1000 else 30.0,
                    items_rendered=100
                )
                monitoring.record_ui_metrics(ui_metrics)
            
            await asyncio.sleep(5)
            
            monitoring.stop()
            
            # Check dashboard status
            print(f"  Checking dashboard status...")
            dashboard_status = monitoring.get_dashboard_status()
            
            if dashboard_status.get("status") != "no_data":
                print(f"    System CPU: {dashboard_status['system']['cpu_percent']:.1f}%")
                print(f"    Downloads: {dashboard_status['downloads']['active_count']} active")
                print(f"    UI response: {dashboard_status['ui']['avg_response_time_ms']:.1f}ms")
                
                results["details"]["dashboard_integration"] = {
                    "has_data": True,
                    "cpu_percent": dashboard_status['system']['cpu_percent'],
                    "active_downloads": dashboard_status['downloads']['active_count']
                }
            else:
                results["errors"].append("Dashboard shows no data despite activity")
            
            # Check alerts
            print(f"  Checking captured alerts...")
            if collected_alerts:
                print(f"    Captured {len(collected_alerts)} alerts:")
                for alert in collected_alerts:
                    print(f"      - {alert.severity}: {alert.metric_name} = {alert.current_value}")
                
                results["details"]["alerts_captured"] = len(collected_alerts)
                results["details"]["alert_metrics"] = [alert.metric_name for alert in collected_alerts]
            else:
                print(f"    No alerts captured (expected if system is healthy)")
                results["details"]["alerts_captured"] = 0
            
            # Test comprehensive report
            print(f"  Generating comprehensive report...")
            report = monitoring.export_performance_report("text", hours=1)
            
            if "PERFORMANCE REPORT" in report and len(report) > 500:
                print(f"    Report generated: {len(report)} characters")
                results["details"]["integrated_report_size"] = len(report)
            else:
                results["errors"].append("Integrated report generation failed")
            
            print(f"✅ Integrated monitoring tests completed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Integrated monitoring failed: {e}")
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all monitoring system tests."""
        print("📊 Starting Performance Monitoring System Tests")
        print("=" * 55)
        
        all_results = {}
        
        # Run all test phases
        test_phases = [
            ("metrics_collection", self.test_metrics_collection),
            ("dashboard_functionality", self.test_dashboard_functionality),
            ("alert_system", self.test_alert_system),
            ("database_operations", self.test_database_operations),
            ("reporting_capabilities", self.test_reporting_capabilities),
            ("integrated_monitoring", self.test_integrated_monitoring)
        ]
        
        passed_count = 0
        
        for phase_name, test_func in test_phases:
            try:
                result = await test_func()
                all_results[phase_name] = result
                
                if result["status"] == "PASSED":
                    passed_count += 1
                    
            except Exception as e:
                all_results[phase_name] = {
                    "status": "FAILED",
                    "errors": [str(e)],
                    "details": {}
                }
        
        # Cleanup
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                shutil.rmtree(os.path.dirname(self.temp_db_path))
                print(f"\n🧹 Cleaned up temporary database")
            except Exception as e:
                print(f"\n⚠️ Cleanup warning: {e}")
        
        # Summary
        print(f"\n📋 Performance Monitoring Test Summary")
        print("=" * 55)
        print(f"✅ Passed: {passed_count}/{len(test_phases)} phases")
        
        if passed_count == len(test_phases):
            print("🎉 ALL MONITORING TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - check details above")
        
        return all_results
    
    def cleanup(self):
        """Cleanup any temporary resources."""
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            try:
                shutil.rmtree(os.path.dirname(self.temp_db_path))
            except Exception:
                pass

async def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Performance Monitoring System Test Runner")
    parser.add_argument("--mode", choices=["all", "metrics", "dashboard", "alerts", "database", "reports", "demo"], 
                       default="all", help="Test mode to run")
    parser.add_argument("--duration", type=float, default=30.0, help="Test duration in seconds")
    
    args = parser.parse_args()
    
    runner = MonitoringTestRunner(duration=args.duration)
    
    try:
        if args.mode == "demo":
            # Run demo from the module
            from monitoring_system import demo_monitoring_system
            await demo_monitoring_system()
        else:
            # Run tests based on mode
            if args.mode == "all":
                await runner.run_all_tests()
            elif args.mode == "metrics":
                await runner.test_metrics_collection()
            elif args.mode == "dashboard":
                await runner.test_dashboard_functionality()
            elif args.mode == "alerts":
                await runner.test_alert_system()
            elif args.mode == "database":
                await runner.test_database_operations()
            elif args.mode == "reports":
                await runner.test_reporting_capabilities()
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
    finally:
        runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 
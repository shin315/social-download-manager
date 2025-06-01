"""
Performance Monitoring and Metrics Collection System
==================================================

This module provides comprehensive performance monitoring and real-time metrics collection 
for Social Download Manager v2.0. Includes performance dashboard, alerts, logging, 
analytics, and user experience tracking.

Key Features:
- Real-time performance dashboard with live metrics
- Comprehensive metrics collection (CPU, memory, disk, network)
- Download speed tracking and analytics
- Performance alerts and notifications
- Historical data storage and trending
- User experience metrics tracking
"""

import asyncio
import time
import threading
import json
import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque, defaultdict
import queue
import psutil
import gc
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics snapshot."""
    timestamp: float
    cpu_percent: float
    memory_usage_mb: float
    memory_percent: float
    disk_usage_gb: float
    disk_percent: float
    network_sent_mb: float
    network_recv_mb: float
    active_threads: int
    gc_collections: int

@dataclass 
class DownloadMetrics:
    """Download-specific performance metrics."""
    timestamp: float
    download_id: str
    url: str
    platform: str
    file_size_mb: float
    download_speed_mbps: float
    time_elapsed: float
    status: str  # 'downloading', 'completed', 'failed', 'paused'
    progress_percent: float
    error_message: Optional[str] = None

@dataclass
class UIMetrics:
    """User interface performance metrics."""
    timestamp: float
    action: str  # 'table_load', 'search', 'filter', 'scroll', 'click'
    response_time_ms: float
    ui_thread_blocked: bool
    memory_usage_mb: float
    fps: float
    items_rendered: int

@dataclass
class AlertConfig:
    """Configuration for performance alerts."""
    metric_name: str
    threshold_value: float
    comparison: str  # 'gt', 'lt', 'eq'
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes default
    severity: str = 'warning'  # 'info', 'warning', 'error', 'critical'

@dataclass
class PerformanceAlert:
    """Performance alert instance."""
    timestamp: float
    metric_name: str
    current_value: float
    threshold_value: float
    severity: str
    message: str
    resolved: bool = False

class MetricsDatabase:
    """Database for storing historical metrics data."""
    
    def __init__(self, db_path: str = "data/database/performance_metrics.db"):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Create database tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    cpu_percent REAL,
                    memory_usage_mb REAL,
                    memory_percent REAL,
                    disk_usage_gb REAL,
                    disk_percent REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    active_threads INTEGER,
                    gc_collections INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    download_id TEXT,
                    url TEXT,
                    platform TEXT,
                    file_size_mb REAL,
                    download_speed_mbps REAL,
                    time_elapsed REAL,
                    status TEXT,
                    progress_percent REAL,
                    error_message TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ui_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    action TEXT,
                    response_time_ms REAL,
                    ui_thread_blocked BOOLEAN,
                    memory_usage_mb REAL,
                    fps REAL,
                    items_rendered INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    metric_name TEXT,
                    current_value REAL,
                    threshold_value REAL,
                    severity TEXT,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """)
            
            # Create indexes for better query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_timestamp ON system_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_download_timestamp ON download_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ui_timestamp ON ui_metrics(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
    
    def store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO system_metrics 
                (timestamp, cpu_percent, memory_usage_mb, memory_percent, 
                 disk_usage_gb, disk_percent, network_sent_mb, network_recv_mb,
                 active_threads, gc_collections)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp, metrics.cpu_percent, metrics.memory_usage_mb,
                metrics.memory_percent, metrics.disk_usage_gb, metrics.disk_percent,
                metrics.network_sent_mb, metrics.network_recv_mb,
                metrics.active_threads, metrics.gc_collections
            ))
    
    def store_download_metrics(self, metrics: DownloadMetrics):
        """Store download metrics in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO download_metrics 
                (timestamp, download_id, url, platform, file_size_mb,
                 download_speed_mbps, time_elapsed, status, progress_percent, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp, metrics.download_id, metrics.url, metrics.platform,
                metrics.file_size_mb, metrics.download_speed_mbps, metrics.time_elapsed,
                metrics.status, metrics.progress_percent, metrics.error_message
            ))
    
    def store_ui_metrics(self, metrics: UIMetrics):
        """Store UI metrics in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO ui_metrics 
                (timestamp, action, response_time_ms, ui_thread_blocked,
                 memory_usage_mb, fps, items_rendered)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp, metrics.action, metrics.response_time_ms,
                metrics.ui_thread_blocked, metrics.memory_usage_mb,
                metrics.fps, metrics.items_rendered
            ))
    
    def store_alert(self, alert: PerformanceAlert):
        """Store alert in database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts 
                (timestamp, metric_name, current_value, threshold_value,
                 severity, message, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.timestamp, alert.metric_name, alert.current_value,
                alert.threshold_value, alert.severity, alert.message, alert.resolved
            ))
    
    def get_system_metrics_range(self, start_time: float, end_time: float) -> List[SystemMetrics]:
        """Get system metrics within time range."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, cpu_percent, memory_usage_mb, memory_percent,
                       disk_usage_gb, disk_percent, network_sent_mb, network_recv_mb,
                       active_threads, gc_collections
                FROM system_metrics
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            """, (start_time, end_time))
            
            return [SystemMetrics(*row) for row in cursor.fetchall()]
    
    def get_download_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get download performance summary for last N hours."""
        start_time = time.time() - (hours * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_downloads,
                    AVG(download_speed_mbps) as avg_speed,
                    MAX(download_speed_mbps) as max_speed,
                    MIN(download_speed_mbps) as min_speed,
                    SUM(file_size_mb) as total_data_mb,
                    AVG(time_elapsed) as avg_duration,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM download_metrics 
                WHERE timestamp > ?
            """, (start_time,))
            
            result = cursor.fetchone()
            if result and result[0] > 0:
                return {
                    "total_downloads": result[0],
                    "avg_speed_mbps": result[1] or 0,
                    "max_speed_mbps": result[2] or 0,
                    "min_speed_mbps": result[3] or 0,
                    "total_data_mb": result[4] or 0,
                    "avg_duration": result[5] or 0,
                    "completed": result[6] or 0,
                    "failed": result[7] or 0,
                    "success_rate": (result[6] or 0) / result[0] * 100
                }
            else:
                return {"total_downloads": 0, "success_rate": 0}

class MetricsCollector:
    """Real-time metrics collection engine."""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.running = False
        self.thread = None
        self.callbacks = []
        self.last_network_stats = None
        
    def add_callback(self, callback: Callable[[SystemMetrics], None]):
        """Add callback for real-time metrics."""
        self.callbacks.append(callback)
    
    def start(self):
        """Start metrics collection."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._collection_loop, daemon=True)
            self.thread.start()
    
    def stop(self):
        """Stop metrics collection."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _collection_loop(self):
        """Main collection loop."""
        while self.running:
            try:
                metrics = self._collect_system_metrics()
                
                # Call all registered callbacks
                for callback in self.callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.error(f"Metrics callback error: {e}")
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network stats
        network = psutil.net_io_counters()
        
        # Calculate network rates
        network_sent_mb = network.bytes_sent / (1024 * 1024)
        network_recv_mb = network.bytes_recv / (1024 * 1024)
        
        # Threading info
        active_threads = threading.active_count()
        
        # Garbage collection stats
        gc_stats = gc.get_stats()
        gc_collections = sum(stat['collections'] for stat in gc_stats)
        
        return SystemMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_usage_mb=memory.used / (1024 * 1024),
            memory_percent=memory.percent,
            disk_usage_gb=disk.used / (1024 * 1024 * 1024),
            disk_percent=(disk.used / disk.total) * 100,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_threads=active_threads,
            gc_collections=gc_collections
        )

class AlertManager:
    """Performance alert management system."""
    
    def __init__(self):
        self.alert_configs = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.callbacks = []
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default alert configurations."""
        default_alerts = [
            AlertConfig("cpu_percent", 90.0, "gt", True, 300, "warning"),
            AlertConfig("memory_percent", 85.0, "gt", True, 300, "warning"), 
            AlertConfig("disk_percent", 90.0, "gt", True, 600, "error"),
            AlertConfig("download_speed_mbps", 0.1, "lt", True, 180, "warning"),
            AlertConfig("ui_response_time_ms", 1000.0, "gt", True, 60, "warning"),
        ]
        
        for alert in default_alerts:
            self.add_alert_config(alert)
    
    def add_alert_config(self, config: AlertConfig):
        """Add alert configuration."""
        self.alert_configs[config.metric_name] = config
    
    def add_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add callback for new alerts."""
        self.callbacks.append(callback)
    
    def check_metric(self, metric_name: str, value: float):
        """Check if metric violates any alert thresholds."""
        if metric_name not in self.alert_configs:
            return
        
        config = self.alert_configs[metric_name]
        if not config.enabled:
            return
        
        # Check if alert should fire
        should_alert = False
        if config.comparison == "gt" and value > config.threshold_value:
            should_alert = True
        elif config.comparison == "lt" and value < config.threshold_value:
            should_alert = True
        elif config.comparison == "eq" and abs(value - config.threshold_value) < 0.01:
            should_alert = True
        
        current_time = time.time()
        
        if should_alert:
            # Check cooldown
            if metric_name in self.active_alerts:
                last_alert_time = self.active_alerts[metric_name].timestamp
                if current_time - last_alert_time < config.cooldown_seconds:
                    return  # Still in cooldown
            
            # Create and fire alert
            alert = PerformanceAlert(
                timestamp=current_time,
                metric_name=metric_name,
                current_value=value,
                threshold_value=config.threshold_value,
                severity=config.severity,
                message=f"{metric_name} is {value:.2f}, exceeds threshold of {config.threshold_value:.2f}"
            )
            
            self.active_alerts[metric_name] = alert
            self.alert_history.append(alert)
            
            # Notify callbacks
            for callback in self.callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
        
        else:
            # Clear active alert if it exists
            if metric_name in self.active_alerts:
                alert = self.active_alerts[metric_name]
                alert.resolved = True
                del self.active_alerts[metric_name]
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get currently active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for last N hours."""
        cutoff_time = time.time() - (hours * 3600)
        return [alert for alert in self.alert_history if alert.timestamp > cutoff_time]

class PerformanceDashboard:
    """Real-time performance dashboard."""
    
    def __init__(self, update_interval: float = 2.0):
        self.update_interval = update_interval
        self.metrics_buffer = deque(maxlen=300)  # 10 minutes at 2s intervals
        self.download_metrics = deque(maxlen=100)
        self.ui_metrics = deque(maxlen=50)
        self.running = False
        
    def add_system_metrics(self, metrics: SystemMetrics):
        """Add system metrics to dashboard."""
        self.metrics_buffer.append(metrics)
    
    def add_download_metrics(self, metrics: DownloadMetrics):
        """Add download metrics to dashboard."""
        self.download_metrics.append(metrics)
    
    def add_ui_metrics(self, metrics: UIMetrics):
        """Add UI metrics to dashboard."""
        self.ui_metrics.append(metrics)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current dashboard status."""
        if not self.metrics_buffer:
            return {"status": "no_data"}
        
        latest = self.metrics_buffer[-1]
        
        # Calculate trends (last 10 data points)
        recent_metrics = list(self.metrics_buffer)[-10:]
        if len(recent_metrics) >= 2:
            cpu_trend = self._calculate_trend([m.cpu_percent for m in recent_metrics])
            memory_trend = self._calculate_trend([m.memory_percent for m in recent_metrics])
        else:
            cpu_trend = memory_trend = 0.0
        
        # Download statistics
        active_downloads = [d for d in self.download_metrics if d.status == 'downloading']
        completed_downloads = [d for d in self.download_metrics if d.status == 'completed']
        
        avg_download_speed = 0.0
        if completed_downloads:
            avg_download_speed = sum(d.download_speed_mbps for d in completed_downloads) / len(completed_downloads)
        
        # UI performance
        recent_ui = list(self.ui_metrics)[-10:]
        avg_ui_response = 0.0
        if recent_ui:
            avg_ui_response = sum(m.response_time_ms for m in recent_ui) / len(recent_ui)
        
        return {
            "timestamp": latest.timestamp,
            "system": {
                "cpu_percent": latest.cpu_percent,
                "cpu_trend": cpu_trend,
                "memory_usage_mb": latest.memory_usage_mb,
                "memory_percent": latest.memory_percent,
                "memory_trend": memory_trend,
                "disk_usage_gb": latest.disk_usage_gb,
                "disk_percent": latest.disk_percent,
                "active_threads": latest.active_threads,
                "gc_collections": latest.gc_collections
            },
            "network": {
                "sent_mb": latest.network_sent_mb,
                "recv_mb": latest.network_recv_mb
            },
            "downloads": {
                "active_count": len(active_downloads),
                "completed_count": len(completed_downloads),
                "avg_speed_mbps": avg_download_speed,
                "total_data_mb": sum(d.file_size_mb for d in completed_downloads)
            },
            "ui": {
                "avg_response_time_ms": avg_ui_response,
                "blocked_operations": len([m for m in recent_ui if m.ui_thread_blocked])
            }
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (positive = increasing, negative = decreasing)."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x_avg = (n - 1) / 2  # Average x value
        y_avg = sum(values) / n  # Average y value
        
        numerator = sum((i - x_avg) * (values[i] - y_avg) for i in range(n))
        denominator = sum((i - x_avg) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def export_dashboard_data(self, format: str = "json") -> str:
        """Export dashboard data in specified format."""
        data = self.get_current_status()
        
        if format == "json":
            return json.dumps(data, indent=2)
        elif format == "text":
            return self._format_text_dashboard(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_text_dashboard(self, data: Dict[str, Any]) -> str:
        """Format dashboard data as text."""
        if data.get("status") == "no_data":
            return "📊 Performance Dashboard - No Data Available"
        
        system = data["system"]
        network = data["network"]
        downloads = data["downloads"]
        ui = data["ui"]
        
        trend_symbol = lambda t: "↗️" if t > 0.5 else "↘️" if t < -0.5 else "➡️"
        
        return f"""📊 Performance Dashboard - {datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')}
{"="*60}

🖥️  SYSTEM PERFORMANCE:
   CPU Usage: {system['cpu_percent']:.1f}% {trend_symbol(system['cpu_trend'])}
   Memory: {system['memory_usage_mb']:.1f} MB ({system['memory_percent']:.1f}%) {trend_symbol(system['memory_trend'])}
   Disk: {system['disk_usage_gb']:.1f} GB ({system['disk_percent']:.1f}%)
   Threads: {system['active_threads']} active
   GC Collections: {system['gc_collections']}

🌐 NETWORK ACTIVITY:
   Sent: {network['sent_mb']:.1f} MB
   Received: {network['recv_mb']:.1f} MB

📥 DOWNLOADS:
   Active: {downloads['active_count']} downloads
   Completed: {downloads['completed_count']} downloads
   Avg Speed: {downloads['avg_speed_mbps']:.2f} MB/s
   Total Data: {downloads['total_data_mb']:.1f} MB

🖱️  UI PERFORMANCE:
   Avg Response Time: {ui['avg_response_time_ms']:.1f} ms
   Blocked Operations: {ui['blocked_operations']}
"""

class PerformanceMonitoringSystem:
    """Main performance monitoring system coordinator."""
    
    def __init__(self, db_path: str = "data/database/performance_metrics.db"):
        self.db = MetricsDatabase(db_path)
        self.collector = MetricsCollector(collection_interval=1.0)
        self.alert_manager = AlertManager()
        self.dashboard = PerformanceDashboard(update_interval=2.0)
        
        # Connect components
        self.collector.add_callback(self._on_system_metrics)
        self.alert_manager.add_callback(self._on_alert)
        
        # Performance log
        self.performance_logger = logging.getLogger('performance')
        self._setup_performance_logging()
    
    def _setup_performance_logging(self):
        """Setup performance-specific logging."""
        handler = logging.FileHandler('logs/performance.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.performance_logger.addHandler(handler)
        self.performance_logger.setLevel(logging.INFO)
    
    def start(self):
        """Start the monitoring system."""
        self.collector.start()
        logger.info("Performance monitoring system started")
    
    def stop(self):
        """Stop the monitoring system."""
        self.collector.stop()
        logger.info("Performance monitoring system stopped")
    
    def _on_system_metrics(self, metrics: SystemMetrics):
        """Handle new system metrics."""
        # Store in database
        self.db.store_system_metrics(metrics)
        
        # Update dashboard
        self.dashboard.add_system_metrics(metrics)
        
        # Check alerts
        self.alert_manager.check_metric("cpu_percent", metrics.cpu_percent)
        self.alert_manager.check_metric("memory_percent", metrics.memory_percent)
        self.alert_manager.check_metric("disk_percent", metrics.disk_percent)
    
    def _on_alert(self, alert: PerformanceAlert):
        """Handle new performance alert."""
        # Store in database
        self.db.store_alert(alert)
        
        # Log alert
        log_level = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }.get(alert.severity, logging.WARNING)
        
        self.performance_logger.log(log_level, f"ALERT: {alert.message}")
        
        # Could add email/SMS notifications here
        print(f"🚨 PERFORMANCE ALERT [{alert.severity.upper()}]: {alert.message}")
    
    def record_download_metrics(self, metrics: DownloadMetrics):
        """Record download-specific metrics."""
        self.db.store_download_metrics(metrics)
        self.dashboard.add_download_metrics(metrics)
        
        # Check download speed alert
        if metrics.status == 'downloading':
            self.alert_manager.check_metric("download_speed_mbps", metrics.download_speed_mbps)
    
    def record_ui_metrics(self, metrics: UIMetrics):
        """Record UI-specific metrics."""
        self.db.store_ui_metrics(metrics)
        self.dashboard.add_ui_metrics(metrics)
        
        # Check UI response time alert
        self.alert_manager.check_metric("ui_response_time_ms", metrics.response_time_ms)
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """Get current dashboard status."""
        return self.dashboard.get_current_status()
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        download_summary = self.db.get_download_summary(hours)
        active_alerts = self.alert_manager.get_active_alerts()
        alert_history = self.alert_manager.get_alert_history(hours)
        dashboard_status = self.dashboard.get_current_status()
        
        return {
            "summary_period_hours": hours,
            "dashboard": dashboard_status,
            "downloads": download_summary,
            "alerts": {
                "active_count": len(active_alerts),
                "active_alerts": [asdict(alert) for alert in active_alerts],
                "history_count": len(alert_history),
                "recent_alerts": [asdict(alert) for alert in alert_history[-10:]]
            },
            "generated_at": time.time()
        }
    
    def export_performance_report(self, format: str = "json", hours: int = 24) -> str:
        """Export comprehensive performance report."""
        summary = self.get_performance_summary(hours)
        
        if format == "json":
            return json.dumps(summary, indent=2)
        elif format == "text":
            return self._format_text_report(summary)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_text_report(self, summary: Dict[str, Any]) -> str:
        """Format performance summary as text report."""
        downloads = summary["downloads"]
        alerts = summary["alerts"]
        dashboard = summary["dashboard"]
        
        report = f"""
📊 SOCIAL DOWNLOAD MANAGER - PERFORMANCE REPORT
{"="*60}
Report Period: Last {summary['summary_period_hours']} hours
Generated: {datetime.fromtimestamp(summary['generated_at']).strftime('%Y-%m-%d %H:%M:%S')}

📥 DOWNLOAD PERFORMANCE:
   Total Downloads: {downloads.get('total_downloads', 0)}
   Success Rate: {downloads.get('success_rate', 0):.1f}%
   Average Speed: {downloads.get('avg_speed_mbps', 0):.2f} MB/s
   Peak Speed: {downloads.get('max_speed_mbps', 0):.2f} MB/s
   Total Data: {downloads.get('total_data_mb', 0):.1f} MB
   Completed: {downloads.get('completed', 0)}
   Failed: {downloads.get('failed', 0)}

🚨 ALERT SUMMARY:
   Active Alerts: {alerts['active_count']}
   Total Alerts (24h): {alerts['history_count']}
"""
        
        if alerts['active_count'] > 0:
            report += "\n   🚨 ACTIVE ALERTS:\n"
            for alert in alerts['active_alerts']:
                report += f"      - {alert['severity'].upper()}: {alert['message']}\n"
        
        if dashboard.get('status') != 'no_data':
            system = dashboard['system']
            report += f"""
🖥️  CURRENT SYSTEM STATUS:
   CPU: {system['cpu_percent']:.1f}%
   Memory: {system['memory_percent']:.1f}% ({system['memory_usage_mb']:.1f} MB)
   Disk: {system['disk_percent']:.1f}% ({system['disk_usage_gb']:.1f} GB)
   Active Threads: {system['active_threads']}
"""
        
        return report

# Demo and testing functions
async def demo_monitoring_system():
    """Demonstrate monitoring system capabilities."""
    print("📊 Performance Monitoring System Demo")
    print("=" * 50)
    
    # Initialize monitoring system
    monitoring = PerformanceMonitoringSystem()
    
    print("🚀 Starting monitoring system...")
    monitoring.start()
    
    try:
        # Simulate some activity
        print("\n📈 Collecting metrics for 10 seconds...")
        await asyncio.sleep(10)
        
        # Simulate download metrics
        print("📥 Simulating download activity...")
        for i in range(3):
            download_metrics = DownloadMetrics(
                timestamp=time.time(),
                download_id=f"download_{i}",
                url=f"https://example.com/video{i}.mp4",
                platform="TikTok" if i % 2 == 0 else "YouTube",
                file_size_mb=25.5 + i * 10,
                download_speed_mbps=5.2 + i * 0.8,
                time_elapsed=30.0 + i * 5,
                status="completed",
                progress_percent=100.0
            )
            monitoring.record_download_metrics(download_metrics)
        
        # Simulate UI metrics
        print("🖱️ Simulating UI activity...")
        for action in ["table_load", "search", "filter", "scroll"]:
            ui_metrics = UIMetrics(
                timestamp=time.time(),
                action=action,
                response_time_ms=150.0 + len(action) * 10,
                ui_thread_blocked=False,
                memory_usage_mb=45.2,
                fps=60.0,
                items_rendered=100
            )
            monitoring.record_ui_metrics(ui_metrics)
        
        await asyncio.sleep(5)
        
        # Get dashboard status
        print("\n📊 Current Dashboard Status:")
        dashboard_text = monitoring.dashboard.export_dashboard_data("text")
        print(dashboard_text)
        
        # Get performance summary
        print("\n📋 Performance Summary:")
        summary_text = monitoring.export_performance_report("text", hours=1)
        print(summary_text)
        
        # Show active alerts
        active_alerts = monitoring.alert_manager.get_active_alerts()
        if active_alerts:
            print(f"\n🚨 Active Alerts ({len(active_alerts)}):")
            for alert in active_alerts:
                print(f"   - {alert.severity.upper()}: {alert.message}")
        else:
            print("\n✅ No active alerts")
        
    finally:
        print("\n🛑 Stopping monitoring system...")
        monitoring.stop()
    
    print("\n✅ Monitoring system demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_monitoring_system()) 
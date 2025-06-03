"""
Performance Reporting for Social Download Manager v2.0

Generates comprehensive performance reports in various formats.
"""

import json
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from .benchmarks import PerformanceMetrics, BenchmarkComparison
from .metrics import MetricsCollector, MetricData
from .profiler import ProfileSession, SystemSnapshot


class ReportFormat(Enum):
    """Available report formats"""
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    CSV = "csv"


@dataclass
class ReportConfig:
    """Configuration for report generation"""
    format: ReportFormat = ReportFormat.HTML
    include_charts: bool = True
    include_raw_data: bool = False
    max_data_points: int = 1000
    time_range_hours: Optional[float] = None


class PerformanceReporter:
    """
    Generates comprehensive performance reports
    """
    
    def __init__(self, output_dir: Union[str, Path] = "scripts/performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_benchmark_report(self, comparison: BenchmarkComparison,
                                config: ReportConfig = None) -> Path:
        """Generate a comprehensive benchmark comparison report"""
        config = config or ReportConfig()
        
        report_data = {
            'title': 'Performance Benchmark Comparison',
            'generated_at': datetime.now().isoformat(),
            'baseline_version': comparison.baseline_metrics.version,
            'current_version': comparison.current_metrics.version,
            'overall_improvement': comparison.overall_improvement,
            'improvements': comparison.improvement_percent,
            'regressions': comparison.regression_percent,
            'summary': comparison.summary,
            'baseline_metrics': comparison.baseline_metrics.to_dict(),
            'current_metrics': comparison.current_metrics.to_dict()
        }
        
        if config.format == ReportFormat.HTML:
            return self._generate_html_report(report_data, "benchmark_comparison")
        elif config.format == ReportFormat.JSON:
            return self._generate_json_report(report_data, "benchmark_comparison")
        elif config.format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(report_data, "benchmark_comparison")
        else:
            return self._generate_text_report(report_data, "benchmark_comparison")
    
    def generate_profiling_report(self, sessions: List[ProfileSession],
                                metrics_collector: Optional[MetricsCollector] = None,
                                config: ReportConfig = None) -> Path:
        """Generate a profiling report from session data"""
        config = config or ReportConfig()
        
        report_data = {
            'title': 'Application Profiling Report',
            'generated_at': datetime.now().isoformat(),
            'total_sessions': len(sessions),
            'sessions': [
                {
                    'session_id': session.session_id,
                    'profiler_type': session.profiler_type.value,
                    'duration': session.end_time - session.start_time if session.end_time else None,
                    'start_time': session.start_time,
                    'end_time': session.end_time,
                    'output_file': str(session.output_file) if session.output_file else None,
                    'metadata': session.metadata
                }
                for session in sessions
            ]
        }
        
        # Add metrics data if available
        if metrics_collector:
            report_data['metrics'] = metrics_collector.export_metrics()
        
        if config.format == ReportFormat.HTML:
            return self._generate_html_report(report_data, "profiling_report")
        elif config.format == ReportFormat.JSON:
            return self._generate_json_report(report_data, "profiling_report")
        elif config.format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(report_data, "profiling_report")
        else:
            return self._generate_text_report(report_data, "profiling_report")
    
    def generate_system_metrics_report(self, snapshots: List[SystemSnapshot],
                                     config: ReportConfig = None) -> Path:
        """Generate a system metrics report"""
        config = config or ReportConfig()
        
        if not snapshots:
            raise ValueError("No system snapshots provided")
        
        # Calculate summary statistics
        cpu_values = [s.cpu_percent for s in snapshots]
        memory_values = [s.memory_percent for s in snapshots]
        memory_used_values = [s.memory_used_mb for s in snapshots]
        
        report_data = {
            'title': 'System Metrics Report',
            'generated_at': datetime.now().isoformat(),
            'total_snapshots': len(snapshots),
            'time_range': {
                'start': snapshots[0].timestamp,
                'end': snapshots[-1].timestamp,
                'duration_seconds': snapshots[-1].timestamp - snapshots[0].timestamp
            },
            'summary': {
                'cpu': {
                    'avg': sum(cpu_values) / len(cpu_values),
                    'max': max(cpu_values),
                    'min': min(cpu_values)
                },
                'memory_percent': {
                    'avg': sum(memory_values) / len(memory_values),
                    'max': max(memory_values),
                    'min': min(memory_values)
                },
                'memory_used_mb': {
                    'avg': sum(memory_used_values) / len(memory_used_values),
                    'max': max(memory_used_values),
                    'min': min(memory_used_values)
                }
            }
        }
        
        # Include raw data if requested
        if config.include_raw_data:
            report_data['snapshots'] = [
                {
                    'timestamp': s.timestamp,
                    'cpu_percent': s.cpu_percent,
                    'memory_percent': s.memory_percent,
                    'memory_used_mb': s.memory_used_mb,
                    'memory_available_mb': s.memory_available_mb,
                    'disk_io_read_mb': s.disk_io_read_mb,
                    'disk_io_write_mb': s.disk_io_write_mb,
                    'network_sent_mb': s.network_sent_mb,
                    'network_recv_mb': s.network_recv_mb,
                    'thread_count': s.thread_count,
                    'process_count': s.process_count
                }
                for s in snapshots[-config.max_data_points:]
            ]
        
        if config.format == ReportFormat.HTML:
            return self._generate_html_report(report_data, "system_metrics")
        elif config.format == ReportFormat.JSON:
            return self._generate_json_report(report_data, "system_metrics")
        elif config.format == ReportFormat.MARKDOWN:
            return self._generate_markdown_report(report_data, "system_metrics")
        else:
            return self._generate_text_report(report_data, "system_metrics")
    
    def _generate_html_report(self, data: Dict[str, Any], report_type: str) -> Path:
        """Generate HTML report"""
        timestamp = int(time.time())
        output_file = self.output_dir / f"{report_type}_{timestamp}.html"
        
        html_content = self._build_html_content(data, report_type)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    def _generate_json_report(self, data: Dict[str, Any], report_type: str) -> Path:
        """Generate JSON report"""
        timestamp = int(time.time())
        output_file = self.output_dir / f"{report_type}_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return output_file
    
    def _generate_markdown_report(self, data: Dict[str, Any], report_type: str) -> Path:
        """Generate Markdown report"""
        timestamp = int(time.time())
        output_file = self.output_dir / f"{report_type}_{timestamp}.md"
        
        markdown_content = self._build_markdown_content(data, report_type)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return output_file
    
    def _generate_text_report(self, data: Dict[str, Any], report_type: str) -> Path:
        """Generate plain text report"""
        timestamp = int(time.time())
        output_file = self.output_dir / f"{report_type}_{timestamp}.txt"
        
        text_content = self._build_text_content(data, report_type)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        return output_file
    
    def _build_html_content(self, data: Dict[str, Any], report_type: str) -> str:
        """Build HTML content for report"""
        title = data.get('title', 'Performance Report')
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .metric {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .improvement {{
            color: #27ae60;
            font-weight: bold;
        }}
        .regression {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .summary-box {{
            background-color: #3498db;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="timestamp">Generated: {data.get('generated_at', 'Unknown')}</p>
        
        {self._build_html_sections(data, report_type)}
    </div>
</body>
</html>
"""
        return html
    
    def _build_html_sections(self, data: Dict[str, Any], report_type: str) -> str:
        """Build HTML sections based on report type"""
        if report_type == "benchmark_comparison":
            return self._build_benchmark_html_sections(data)
        elif report_type == "profiling_report":
            return self._build_profiling_html_sections(data)
        elif report_type == "system_metrics":
            return self._build_system_metrics_html_sections(data)
        else:
            return "<p>Unknown report type</p>"
    
    def _build_benchmark_html_sections(self, data: Dict[str, Any]) -> str:
        """Build HTML sections for benchmark report"""
        html = f"""
        <div class="summary-box">
            <h2>Executive Summary</h2>
            <p><strong>Comparing:</strong> {data.get('baseline_version')} vs {data.get('current_version')}</p>
            <p><strong>Overall Performance Change:</strong> 
            <span class="{'improvement' if data.get('overall_improvement', 0) > 0 else 'regression'}">
                {data.get('overall_improvement', 0):+.1f}%
            </span></p>
        </div>
        """
        
        # Improvements section
        improvements = data.get('improvements', {})
        if improvements:
            html += "<h2>🚀 Performance Improvements</h2>"
            for metric, percent in improvements.items():
                html += f'<div class="metric improvement">• {metric.replace("_", " ").title()}: +{percent:.1f}%</div>'
        
        # Regressions section
        regressions = data.get('regressions', {})
        if regressions:
            html += "<h2>⚠️ Performance Regressions</h2>"
            for metric, percent in regressions.items():
                html += f'<div class="metric regression">• {metric.replace("_", " ").title()}: -{percent:.1f}%</div>'
        
        return html
    
    def _build_profiling_html_sections(self, data: Dict[str, Any]) -> str:
        """Build HTML sections for profiling report"""
        html = f"""
        <div class="summary-box">
            <h2>Profiling Summary</h2>
            <p><strong>Total Sessions:</strong> {data.get('total_sessions', 0)}</p>
        </div>
        
        <h2>Profiling Sessions</h2>
        <table>
            <tr>
                <th>Session ID</th>
                <th>Type</th>
                <th>Duration (s)</th>
                <th>Status</th>
            </tr>
        """
        
        for session in data.get('sessions', []):
            duration = session.get('duration')
            duration_str = f"{duration:.3f}" if duration else "N/A"
            html += f"""
            <tr>
                <td>{session.get('session_id')}</td>
                <td>{session.get('profiler_type')}</td>
                <td>{duration_str}</td>
                <td>{'Complete' if session.get('end_time') else 'Running'}</td>
            </tr>
            """
        
        html += "</table>"
        return html
    
    def _build_system_metrics_html_sections(self, data: Dict[str, Any]) -> str:
        """Build HTML sections for system metrics report"""
        summary = data.get('summary', {})
        
        html = f"""
        <div class="summary-box">
            <h2>System Metrics Summary</h2>
            <p><strong>Total Snapshots:</strong> {data.get('total_snapshots', 0)}</p>
            <p><strong>Duration:</strong> {data.get('time_range', {}).get('duration_seconds', 0):.1f} seconds</p>
        </div>
        
        <h2>Resource Usage Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Average</th>
                <th>Maximum</th>
                <th>Minimum</th>
            </tr>
        """
        
        for metric_name, values in summary.items():
            if isinstance(values, dict):
                html += f"""
                <tr>
                    <td>{metric_name.replace('_', ' ').title()}</td>
                    <td>{values.get('avg', 0):.2f}</td>
                    <td>{values.get('max', 0):.2f}</td>
                    <td>{values.get('min', 0):.2f}</td>
                </tr>
                """
        
        html += "</table>"
        return html
    
    def _build_markdown_content(self, data: Dict[str, Any], report_type: str) -> str:
        """Build Markdown content for report"""
        title = data.get('title', 'Performance Report')
        
        markdown = f"""# {title}

Generated: {data.get('generated_at', 'Unknown')}

"""
        
        if report_type == "benchmark_comparison":
            markdown += self._build_benchmark_markdown_sections(data)
        elif report_type == "profiling_report":
            markdown += self._build_profiling_markdown_sections(data)
        elif report_type == "system_metrics":
            markdown += self._build_system_metrics_markdown_sections(data)
        
        return markdown
    
    def _build_benchmark_markdown_sections(self, data: Dict[str, Any]) -> str:
        """Build Markdown sections for benchmark report"""
        markdown = f"""## Executive Summary

**Comparing:** {data.get('baseline_version')} vs {data.get('current_version')}  
**Overall Performance Change:** {data.get('overall_improvement', 0):+.1f}%

"""
        
        improvements = data.get('improvements', {})
        if improvements:
            markdown += "## 🚀 Performance Improvements\n\n"
            for metric, percent in improvements.items():
                markdown += f"- {metric.replace('_', ' ').title()}: +{percent:.1f}%\n"
            markdown += "\n"
        
        regressions = data.get('regressions', {})
        if regressions:
            markdown += "## ⚠️ Performance Regressions\n\n"
            for metric, percent in regressions.items():
                markdown += f"- {metric.replace('_', ' ').title()}: -{percent:.1f}%\n"
            markdown += "\n"
        
        return markdown
    
    def _build_profiling_markdown_sections(self, data: Dict[str, Any]) -> str:
        """Build Markdown sections for profiling report"""
        markdown = f"""## Profiling Summary

**Total Sessions:** {data.get('total_sessions', 0)}

## Profiling Sessions

| Session ID | Type | Duration (s) | Status |
|------------|------|--------------|--------|
"""
        
        for session in data.get('sessions', []):
            duration = session.get('duration')
            duration_str = f"{duration:.3f}" if duration else "N/A"
            status = "Complete" if session.get('end_time') else "Running"
            markdown += f"| {session.get('session_id')} | {session.get('profiler_type')} | {duration_str} | {status} |\n"
        
        return markdown
    
    def _build_system_metrics_markdown_sections(self, data: Dict[str, Any]) -> str:
        """Build Markdown sections for system metrics report"""
        summary = data.get('summary', {})
        
        markdown = f"""## System Metrics Summary

**Total Snapshots:** {data.get('total_snapshots', 0)}  
**Duration:** {data.get('time_range', {}).get('duration_seconds', 0):.1f} seconds

## Resource Usage Summary

| Metric | Average | Maximum | Minimum |
|--------|---------|---------|---------|
"""
        
        for metric_name, values in summary.items():
            if isinstance(values, dict):
                markdown += f"| {metric_name.replace('_', ' ').title()} | {values.get('avg', 0):.2f} | {values.get('max', 0):.2f} | {values.get('min', 0):.2f} |\n"
        
        return markdown
    
    def _build_text_content(self, data: Dict[str, Any], report_type: str) -> str:
        """Build plain text content for report"""
        title = data.get('title', 'Performance Report')
        
        text = f"""{title}
{'=' * len(title)}

Generated: {data.get('generated_at', 'Unknown')}

"""
        
        if report_type == "benchmark_comparison":
            text += self._build_benchmark_text_sections(data)
        elif report_type == "profiling_report":
            text += self._build_profiling_text_sections(data)
        elif report_type == "system_metrics":
            text += self._build_system_metrics_text_sections(data)
        
        return text
    
    def _build_benchmark_text_sections(self, data: Dict[str, Any]) -> str:
        """Build text sections for benchmark report"""
        text = f"""EXECUTIVE SUMMARY
-----------------
Comparing: {data.get('baseline_version')} vs {data.get('current_version')}
Overall Performance Change: {data.get('overall_improvement', 0):+.1f}%

"""
        
        improvements = data.get('improvements', {})
        if improvements:
            text += "PERFORMANCE IMPROVEMENTS\n"
            text += "------------------------\n"
            for metric, percent in improvements.items():
                text += f"• {metric.replace('_', ' ').title()}: +{percent:.1f}%\n"
            text += "\n"
        
        regressions = data.get('regressions', {})
        if regressions:
            text += "PERFORMANCE REGRESSIONS\n"
            text += "-----------------------\n"
            for metric, percent in regressions.items():
                text += f"• {metric.replace('_', ' ').title()}: -{percent:.1f}%\n"
            text += "\n"
        
        return text
    
    def _build_profiling_text_sections(self, data: Dict[str, Any]) -> str:
        """Build text sections for profiling report"""
        text = f"""PROFILING SUMMARY
-----------------
Total Sessions: {data.get('total_sessions', 0)}

PROFILING SESSIONS
------------------
"""
        
        for session in data.get('sessions', []):
            duration = session.get('duration')
            duration_str = f"{duration:.3f}s" if duration else "N/A"
            status = "Complete" if session.get('end_time') else "Running"
            text += f"• {session.get('session_id')} ({session.get('profiler_type')}) - {duration_str} - {status}\n"
        
        return text
    
    def _build_system_metrics_text_sections(self, data: Dict[str, Any]) -> str:
        """Build text sections for system metrics report"""
        summary = data.get('summary', {})
        
        text = f"""SYSTEM METRICS SUMMARY
----------------------
Total Snapshots: {data.get('total_snapshots', 0)}
Duration: {data.get('time_range', {}).get('duration_seconds', 0):.1f} seconds

RESOURCE USAGE SUMMARY
----------------------
"""
        
        for metric_name, values in summary.items():
            if isinstance(values, dict):
                text += f"{metric_name.replace('_', ' ').title()}:\n"
                text += f"  Average: {values.get('avg', 0):.2f}\n"
                text += f"  Maximum: {values.get('max', 0):.2f}\n"
                text += f"  Minimum: {values.get('min', 0):.2f}\n\n"
        
        return text 
"""
Database Performance Optimizer for Social Download Manager v2.0

Implements comprehensive database optimization including:
- Query analysis and optimization
- Index management and recommendations
- Connection pooling optimization
- Query result caching
- Performance monitoring and alerting
"""

import sqlite3
import time
import hashlib
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import json

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class QueryAnalysisResult:
    """Results of query analysis"""
    query_hash: str
    original_query: str
    complexity_score: int
    has_indexes: bool
    missing_indexes: List[str]
    suggestions: List[str]
    estimated_cost: float
    execution_plan: List[Dict[str, Any]]


@dataclass
class DatabaseMetrics:
    """Database performance metrics"""
    timestamp: datetime
    total_connections: int
    active_connections: int
    query_count: int
    avg_query_time_ms: float
    slow_query_count: int
    cache_hit_ratio: float
    database_size_mb: float
    index_usage_stats: Dict[str, int]


class SQLiteOptimizer:
    """
    SQLite-specific database optimizer
    """
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._query_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
        self._query_stats: Dict[str, List[float]] = defaultdict(list)
        self._slow_query_threshold = 100.0  # 100ms
        
        # Performance settings
        self.optimization_settings = {
            'journal_mode': 'WAL',
            'synchronous': 'NORMAL', 
            'cache_size': -64000,  # 64MB
            'temp_store': 'MEMORY',
            'mmap_size': 268435456,  # 256MB
            'page_size': 4096,
            'foreign_keys': True,
            'optimize_frequency': 3600  # 1 hour
        }
    
    def optimize_database_settings(self) -> Dict[str, Any]:
        """Apply optimal database settings"""
        results = {}
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Apply each optimization setting
                for setting, value in self.optimization_settings.items():
                    if setting == 'optimize_frequency':
                        continue  # Not a PRAGMA setting
                    
                    if isinstance(value, bool):
                        pragma_value = 'ON' if value else 'OFF'
                    else:
                        pragma_value = str(value)
                    
                    pragma_command = f"PRAGMA {setting} = {pragma_value}"
                    
                    try:
                        cursor.execute(pragma_command)
                        # Verify setting was applied
                        cursor.execute(f"PRAGMA {setting}")
                        current_value = cursor.fetchone()[0]
                        results[setting] = {
                            'applied': pragma_value,
                            'current': current_value,
                            'success': True
                        }
                        self.logger.info(f"Applied PRAGMA {setting} = {pragma_value}")
                    except Exception as e:
                        results[setting] = {
                            'applied': pragma_value,
                            'error': str(e),
                            'success': False
                        }
                        self.logger.error(f"Failed to apply PRAGMA {setting}: {e}")
                
                # Run optimization
                cursor.execute("PRAGMA optimize")
                results['optimize'] = {'success': True}
                
        except Exception as e:
            self.logger.error(f"Database optimization failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def analyze_query_performance(self, query: str, params: Optional[Tuple] = None) -> QueryAnalysisResult:
        """Analyze query performance and provide optimization suggestions"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Get query execution plan
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                cursor.execute(explain_query, params or ())
                execution_plan = [
                    {
                        'id': row[0],
                        'parent': row[1], 
                        'notused': row[2],
                        'detail': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                
                # Analyze query complexity
                complexity_score = self._calculate_query_complexity(query, execution_plan)
                
                # Check for missing indexes
                missing_indexes = self._identify_missing_indexes(query, execution_plan)
                
                # Generate optimization suggestions
                suggestions = self._generate_optimization_suggestions(query, execution_plan, missing_indexes)
                
                # Check if query uses indexes
                has_indexes = any('USING INDEX' in step['detail'] for step in execution_plan)
                
                # Estimate query cost
                estimated_cost = self._estimate_query_cost(execution_plan)
                
        except Exception as e:
            self.logger.error(f"Query analysis failed: {e}")
            return QueryAnalysisResult(
                query_hash=query_hash,
                original_query=query,
                complexity_score=10,
                has_indexes=False,
                missing_indexes=[],
                suggestions=[f"Query analysis failed: {e}"],
                estimated_cost=1000.0,
                execution_plan=[]
            )
        
        return QueryAnalysisResult(
            query_hash=query_hash,
            original_query=query,
            complexity_score=complexity_score,
            has_indexes=has_indexes,
            missing_indexes=missing_indexes,
            suggestions=suggestions,
            estimated_cost=estimated_cost,
            execution_plan=execution_plan
        )
    
    def _calculate_query_complexity(self, query: str, execution_plan: List[Dict]) -> int:
        """Calculate query complexity score (1-10)"""
        complexity = 1
        query_upper = query.upper()
        
        # Basic query complexity factors
        complexity += query_upper.count('JOIN')
        complexity += query_upper.count('UNION') * 2
        complexity += query_upper.count('SUBQUERY') * 2
        complexity += query_upper.count('ORDER BY')
        complexity += query_upper.count('GROUP BY')
        complexity += query_upper.count('HAVING')
        
        # Execution plan complexity
        complexity += len(execution_plan)
        
        # Scan operations are expensive
        scan_operations = sum(1 for step in execution_plan if 'SCAN' in step['detail'])
        complexity += scan_operations * 2
        
        return min(complexity, 10)
    
    def _identify_missing_indexes(self, query: str, execution_plan: List[Dict]) -> List[str]:
        """Identify missing indexes that could improve performance"""
        missing_indexes = []
        
        for step in execution_plan:
            detail = step['detail']
            
            # Look for table scans that could benefit from indexes
            if 'SCAN TABLE' in detail and 'USING INDEX' not in detail:
                # Extract table name and potential columns
                if 'content' in detail.lower():
                    if 'platform_id' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_content_platform_id ON content(platform_id)")
                    if 'status' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_content_status ON content(status)")
                    if 'created_at' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_content_created_at ON content(created_at)")
                
                elif 'downloads' in detail.lower():
                    if 'content_id' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_downloads_content_id ON downloads(content_id)")
                    if 'status' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_downloads_status ON downloads(status)")
                
                elif 'content_metadata' in detail.lower():
                    if 'content_id' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_content_metadata_content_id ON content_metadata(content_id)")
                    if 'metadata_type' in query.lower():
                        missing_indexes.append("CREATE INDEX idx_content_metadata_type_key ON content_metadata(metadata_type, metadata_key)")
        
        return list(set(missing_indexes))  # Remove duplicates
    
    def _generate_optimization_suggestions(self, query: str, execution_plan: List[Dict], missing_indexes: List[str]) -> List[str]:
        """Generate optimization suggestions"""
        suggestions = []
        query_upper = query.upper()
        
        # Index suggestions
        if missing_indexes:
            suggestions.append(f"Consider adding {len(missing_indexes)} missing indexes for better performance")
        
        # Query structure suggestions
        if 'SELECT *' in query_upper:
            suggestions.append("Consider selecting only required columns instead of SELECT *")
        
        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            suggestions.append("Consider adding LIMIT clause when using ORDER BY")
        
        if query_upper.count('JOIN') > 2:
            suggestions.append("Complex query with multiple JOINs - consider breaking into smaller queries")
        
        if 'LIKE' in query_upper and not any('INDEX' in step['detail'] for step in execution_plan):
            suggestions.append("LIKE operations without indexes can be slow - consider full-text search")
        
        # Scan operations
        scan_count = sum(1 for step in execution_plan if 'SCAN' in step['detail'])
        if scan_count > 1:
            suggestions.append(f"Query performs {scan_count} table scans - consider adding indexes")
        
        if not suggestions:
            suggestions.append("Query appears well optimized")
        
        return suggestions
    
    def _estimate_query_cost(self, execution_plan: List[Dict]) -> float:
        """Estimate query execution cost"""
        cost = 0.0
        
        for step in execution_plan:
            detail = step['detail']
            
            # Different operations have different costs
            if 'SCAN TABLE' in detail:
                cost += 100.0  # Table scans are expensive
            elif 'SEARCH TABLE' in detail and 'USING INDEX' in detail:
                cost += 1.0   # Index searches are cheap
            elif 'USE TEMP B-TREE' in detail:
                cost += 50.0  # Temporary structures are moderate cost
            elif 'COMPOUND SUBQUERIES' in detail:
                cost += 25.0  # Subqueries add cost
            else:
                cost += 5.0   # Default cost
        
        return cost
    
    def create_recommended_indexes(self, analysis_results: List[QueryAnalysisResult]) -> Dict[str, Any]:
        """Create recommended indexes based on query analysis"""
        # Collect all missing indexes
        all_missing_indexes = []
        for result in analysis_results:
            all_missing_indexes.extend(result.missing_indexes)
        
        # Count frequency of each index suggestion
        index_frequency = defaultdict(int)
        for index in all_missing_indexes:
            index_frequency[index] += 1
        
        # Sort by frequency (most needed first)
        sorted_indexes = sorted(index_frequency.items(), key=lambda x: x[1], reverse=True)
        
        results = {
            'total_recommendations': len(sorted_indexes),
            'created_indexes': [],
            'failed_indexes': [],
            'skipped_indexes': []
        }
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                for index_sql, frequency in sorted_indexes:
                    try:
                        # Check if index already exists
                        index_name = self._extract_index_name(index_sql)
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
                        
                        if cursor.fetchone():
                            results['skipped_indexes'].append({
                                'sql': index_sql,
                                'reason': 'Already exists',
                                'frequency': frequency
                            })
                            continue
                        
                        # Create the index
                        start_time = time.time()
                        cursor.execute(index_sql)
                        creation_time = time.time() - start_time
                        
                        results['created_indexes'].append({
                            'sql': index_sql,
                            'name': index_name,
                            'frequency': frequency,
                            'creation_time_ms': creation_time * 1000
                        })
                        
                        self.logger.info(f"Created index {index_name} in {creation_time*1000:.1f}ms")
                        
                    except Exception as e:
                        results['failed_indexes'].append({
                            'sql': index_sql,
                            'error': str(e),
                            'frequency': frequency
                        })
                        self.logger.error(f"Failed to create index: {e}")
                
        except Exception as e:
            results['error'] = str(e)
            self.logger.error(f"Index creation failed: {e}")
        
        return results
    
    def _extract_index_name(self, index_sql: str) -> str:
        """Extract index name from CREATE INDEX SQL"""
        parts = index_sql.split()
        try:
            index_pos = parts.index('INDEX')
            return parts[index_pos + 1]
        except (ValueError, IndexError):
            return "unknown_index"
    
    def optimize_query_result_caching(self, enable_cache: bool = True, max_cache_size: int = 1000) -> Dict[str, Any]:
        """Configure query result caching"""
        if enable_cache:
            self._query_cache = {}
            self._cache_max_size = max_cache_size
            return {
                'caching_enabled': True,
                'max_cache_size': max_cache_size,
                'current_cache_size': 0
            }
        else:
            self._query_cache.clear()
            return {
                'caching_enabled': False,
                'cache_cleared': True
            }
    
    def execute_optimized_query(self, query: str, params: Optional[Tuple] = None, use_cache: bool = True) -> Tuple[List[Any], float]:
        """Execute query with optimization and caching"""
        query_hash = hashlib.md5(f"{query}{params}".encode()).hexdigest()
        
        # Check cache first
        if use_cache and query_hash in self._query_cache:
            with self._cache_lock:
                cached_result = self._query_cache[query_hash]
                return cached_result['data'], 0.0  # Cache hit = 0ms
        
        # Execute query with timing
        start_time = time.time()
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}")
            raise
        
        execution_time = time.time() - start_time
        
        # Cache results if enabled
        if use_cache and execution_time > 0.01:  # Only cache queries > 10ms
            with self._cache_lock:
                if len(self._query_cache) >= self._cache_max_size:
                    # Remove oldest entry
                    oldest_key = next(iter(self._query_cache))
                    del self._query_cache[oldest_key]
                
                self._query_cache[query_hash] = {
                    'data': results,
                    'timestamp': time.time(),
                    'execution_time': execution_time
                }
        
        # Record query statistics
        self._query_stats[query_hash].append(execution_time * 1000)  # Convert to ms
        
        return results, execution_time
    
    def get_database_metrics(self) -> DatabaseMetrics:
        """Collect comprehensive database metrics"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Database size
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)
                
                # Index usage stats (simplified)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = [row[0] for row in cursor.fetchall()]
                index_usage_stats = {idx: 0 for idx in indexes}  # Placeholder
                
                # Query statistics
                total_queries = sum(len(times) for times in self._query_stats.values())
                if total_queries > 0:
                    all_times = [time for times in self._query_stats.values() for time in times]
                    avg_query_time = sum(all_times) / len(all_times)
                    slow_queries = sum(1 for time in all_times if time > self._slow_query_threshold)
                else:
                    avg_query_time = 0.0
                    slow_queries = 0
                
                # Cache metrics
                cache_hit_ratio = 0.0
                if hasattr(self, '_cache_max_size'):
                    cache_hit_ratio = len(self._query_cache) / max(self._cache_max_size, 1)
                
        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")
            return DatabaseMetrics(
                timestamp=datetime.now(),
                total_connections=0,
                active_connections=0,
                query_count=0,
                avg_query_time_ms=0.0,
                slow_query_count=0,
                cache_hit_ratio=0.0,
                database_size_mb=0.0,
                index_usage_stats={}
            )
        
        return DatabaseMetrics(
            timestamp=datetime.now(),
            total_connections=1,  # SQLite single connection
            active_connections=1,
            query_count=total_queries,
            avg_query_time_ms=avg_query_time,
            slow_query_count=slow_queries,
            cache_hit_ratio=cache_hit_ratio,
            database_size_mb=db_size_mb,
            index_usage_stats=index_usage_stats
        )
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive database performance report"""
        metrics = self.get_database_metrics()
        
        # Analyze slow queries
        slow_query_analysis = []
        for query_hash, times in self._query_stats.items():
            avg_time = sum(times) / len(times)
            if avg_time > self._slow_query_threshold:
                slow_query_analysis.append({
                    'query_hash': query_hash,
                    'avg_time_ms': avg_time,
                    'max_time_ms': max(times),
                    'execution_count': len(times)
                })
        
        # Sort by average time
        slow_query_analysis.sort(key=lambda x: x['avg_time_ms'], reverse=True)
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'database_file': str(self.db_path),
            'database_size_mb': metrics.database_size_mb,
            'total_queries_analyzed': metrics.query_count,
            'average_query_time_ms': metrics.avg_query_time_ms,
            'slow_query_count': metrics.slow_query_count,
            'slow_query_threshold_ms': self._slow_query_threshold,
            'cache_hit_ratio': metrics.cache_hit_ratio,
            'index_count': len(metrics.index_usage_stats),
            'slow_queries': slow_query_analysis[:10],  # Top 10 slow queries
            'optimization_settings': self.optimization_settings,
            'recommendations': self._generate_performance_recommendations(metrics, slow_query_analysis)
        }
    
    def _generate_performance_recommendations(self, metrics: DatabaseMetrics, slow_queries: List[Dict]) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Database size recommendations
        if metrics.database_size_mb > 1000:  # 1GB
            recommendations.append("Large database detected - consider archiving old data")
        
        # Query performance recommendations
        if metrics.avg_query_time_ms > 50:
            recommendations.append("High average query time - review query optimization and indexing")
        
        if metrics.slow_query_count > metrics.query_count * 0.1:  # >10% slow queries
            recommendations.append("High percentage of slow queries - investigate query patterns")
        
        # Cache recommendations
        if metrics.cache_hit_ratio < 0.5:
            recommendations.append("Low cache utilization - consider increasing cache size or TTL")
        
        # Slow query recommendations
        if len(slow_queries) > 5:
            recommendations.append("Multiple slow queries detected - run query analysis and create indexes")
        
        # Index recommendations
        if len(metrics.index_usage_stats) < 10:
            recommendations.append("Few indexes detected - consider creating indexes for common queries")
        
        if not recommendations:
            recommendations.append("Database performance appears optimal")
        
        return recommendations


class DatabasePerformanceOptimizer:
    """
    Main database performance optimizer orchestrating all optimization strategies
    """
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.sqlite_optimizer = SQLiteOptimizer(db_path)
        self.logger = logging.getLogger(__name__)
        
        # Common queries for analysis
        self.common_queries = [
            # Content queries
            ("content_by_platform", "SELECT * FROM content WHERE platform_id = ? AND status = 'completed' ORDER BY created_at DESC LIMIT 50", (1,)),
            ("content_search", "SELECT * FROM content WHERE title LIKE ? AND is_deleted = 0", ('%test%',)),
            ("content_with_metadata", """
                SELECT c.*, cm.metadata_value 
                FROM content c 
                LEFT JOIN content_metadata cm ON c.id = cm.content_id 
                WHERE cm.metadata_type = 'platform_specific' AND c.platform_id = ?
            """, (1,)),
            
            # Download queries
            ("active_downloads", "SELECT * FROM downloads WHERE status IN ('queued', 'downloading', 'processing')", ()),
            ("download_history", "SELECT * FROM downloads WHERE created_at >= ? AND status = 'completed'", ('2024-01-01',)),
            ("download_errors", "SELECT * FROM download_errors WHERE is_resolved = 0 ORDER BY occurred_at DESC", ()),
            
            # Analytics queries
            ("platform_stats", """
                SELECT p.name, COUNT(*) as content_count 
                FROM content c 
                JOIN platforms p ON c.platform_id = p.id 
                WHERE c.is_deleted = 0 
                GROUP BY p.name
            """, ()),
            ("metadata_aggregation", """
                SELECT metadata_type, COUNT(*) as count 
                FROM content_metadata 
                GROUP BY metadata_type 
                ORDER BY count DESC
            """, ()),
        ]
        
        # Test query patterns (updated for simple schema)
        self.test_queries = {
            'content_by_platform': {
                'sql': "SELECT * FROM content WHERE platform = ? AND status != 'failed' ORDER BY created_at DESC LIMIT 20",
                'params': ['youtube'],
                'description': 'Fetch recent content from specific platform'
            },
            'content_search': {
                'sql': "SELECT * FROM content WHERE (title LIKE ? OR description LIKE ?) AND status = 'completed'",
                'params': ['%video%', '%test%'],
                'description': 'Search content by title/description'
            },
            'downloads_with_content': {
                'sql': """
                SELECT c.title, c.author, d.status, d.progress_percentage, d.quality 
                FROM downloads d 
                JOIN content c ON d.content_id = c.id 
                WHERE d.status IN ('downloading', 'queued') 
                ORDER BY d.created_at DESC
                """,
                'params': [],
                'description': 'Active downloads with content metadata'
            },
            'active_downloads': {
                'sql': "SELECT * FROM downloads WHERE status IN ('downloading', 'queued') ORDER BY created_at",
                'params': [],
                'description': 'Currently active downloads'
            },
            'download_errors': {
                'sql': """
                SELECT de.error_type, de.error_message, c.title, c.url 
                FROM download_errors de 
                JOIN downloads d ON de.download_id = d.id 
                JOIN content c ON d.content_id = c.id 
                WHERE de.created_at > datetime('now', '-7 days')
                """,
                'params': [],
                'description': 'Recent download errors with context'
            },
            'platform_stats': {
                'sql': """
                SELECT platform, 
                       COUNT(*) as total_content,
                       COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                       AVG(view_count) as avg_views
                FROM content 
                GROUP BY platform
                """,
                'params': [],
                'description': 'Platform statistics aggregation'
            },
            'user_activity': {
                'sql': """
                SELECT author,
                       COUNT(*) as content_count,
                       SUM(view_count) as total_views,
                       AVG(like_count) as avg_likes
                FROM content 
                WHERE author IS NOT NULL 
                GROUP BY author 
                ORDER BY content_count DESC
                """,
                'params': [],
                'description': 'Content creator statistics'
            }
        }
    
    def run_comprehensive_optimization(self) -> Dict[str, Any]:
        """Run comprehensive database optimization"""
        self.logger.info("Starting comprehensive database optimization")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'optimization_steps': {},
            'performance_improvements': {},
            'recommendations': []
        }
        
        try:
            # Step 1: Apply database settings optimization
            self.logger.info("Step 1: Optimizing database settings")
            settings_result = self.sqlite_optimizer.optimize_database_settings()
            results['optimization_steps']['database_settings'] = settings_result
            
            # Step 2: Analyze common queries
            self.logger.info("Step 2: Analyzing common query patterns")
            query_analysis_results = []
            for query_name, query, params in self.common_queries:
                try:
                    analysis = self.sqlite_optimizer.analyze_query_performance(query, params)
                    query_analysis_results.append(analysis)
                    self.logger.debug(f"Analyzed query '{query_name}': complexity={analysis.complexity_score}")
                except Exception as e:
                    self.logger.error(f"Failed to analyze query '{query_name}': {e}")
            
            results['optimization_steps']['query_analysis'] = {
                'total_queries_analyzed': len(query_analysis_results),
                'average_complexity': sum(r.complexity_score for r in query_analysis_results) / max(len(query_analysis_results), 1),
                'queries_with_missing_indexes': sum(1 for r in query_analysis_results if r.missing_indexes)
            }
            
            # Step 3: Create recommended indexes
            self.logger.info("Step 3: Creating recommended indexes")
            index_creation_result = self.sqlite_optimizer.create_recommended_indexes(query_analysis_results)
            results['optimization_steps']['index_creation'] = index_creation_result
            
            # Step 4: Enable query caching
            self.logger.info("Step 4: Configuring query result caching")
            cache_config = self.sqlite_optimizer.optimize_query_result_caching(enable_cache=True, max_cache_size=1000)
            results['optimization_steps']['query_caching'] = cache_config
            
            # Step 5: Benchmark performance improvements
            self.logger.info("Step 5: Benchmarking performance improvements")
            performance_improvements = self._benchmark_performance_improvements()
            results['performance_improvements'] = performance_improvements
            
            # Step 6: Generate final recommendations
            performance_report = self.sqlite_optimizer.generate_performance_report()
            results['recommendations'] = performance_report['recommendations']
            
        except Exception as e:
            self.logger.error(f"Comprehensive optimization failed: {e}")
            results['error'] = str(e)
        
        results['end_time'] = datetime.now().isoformat()
        results['total_duration_seconds'] = (datetime.fromisoformat(results['end_time']) - 
                                           datetime.fromisoformat(results['start_time'])).total_seconds()
        
        return results
    
    def _benchmark_performance_improvements(self) -> Dict[str, Any]:
        """Benchmark performance improvements"""
        improvements = {
            'query_performance': {},
            'overall_improvement_percent': 0.0
        }
        
        total_improvement = 0.0
        query_count = 0
        
        for query_name, query, params in self.common_queries:
            try:
                # Execute query and measure performance
                start_time = time.time()
                results, query_time = self.sqlite_optimizer.execute_optimized_query(query, params, use_cache=False)
                total_time = time.time() - start_time
                
                improvements['query_performance'][query_name] = {
                    'execution_time_ms': query_time * 1000,
                    'total_time_ms': total_time * 1000,
                    'result_count': len(results),
                    'cached': False
                }
                
                # Execute again to test caching
                start_time = time.time()
                cached_results, cached_query_time = self.sqlite_optimizer.execute_optimized_query(query, params, use_cache=True)
                cached_total_time = time.time() - start_time
                
                if cached_query_time == 0.0:  # Cache hit
                    cache_improvement = ((total_time - cached_total_time) / total_time) * 100
                    improvements['query_performance'][query_name]['cache_improvement_percent'] = cache_improvement
                    total_improvement += cache_improvement
                    query_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to benchmark query '{query_name}': {e}")
                improvements['query_performance'][query_name] = {'error': str(e)}
        
        if query_count > 0:
            improvements['overall_improvement_percent'] = total_improvement / query_count
        
        return improvements
    
    def monitor_database_health(self) -> Dict[str, Any]:
        """Monitor ongoing database health and performance"""
        metrics = self.sqlite_optimizer.get_database_metrics()
        
        health_status = {
            'timestamp': metrics.timestamp.isoformat(),
            'overall_health': 'good',  # good, warning, critical
            'metrics': {
                'database_size_mb': metrics.database_size_mb,
                'query_count': metrics.query_count,
                'avg_query_time_ms': metrics.avg_query_time_ms,
                'slow_query_count': metrics.slow_query_count,
                'cache_hit_ratio': metrics.cache_hit_ratio
            },
            'alerts': []
        }
        
        # Health checks
        if metrics.avg_query_time_ms > 100:
            health_status['alerts'].append("High average query time detected")
            health_status['overall_health'] = 'warning'
        
        if metrics.slow_query_count > metrics.query_count * 0.2:
            health_status['alerts'].append("High percentage of slow queries")
            health_status['overall_health'] = 'critical'
        
        if metrics.database_size_mb > 2000:  # 2GB
            health_status['alerts'].append("Database size is very large")
            if health_status['overall_health'] == 'good':
                health_status['overall_health'] = 'warning'
        
        if metrics.cache_hit_ratio < 0.3:
            health_status['alerts'].append("Low cache efficiency")
        
        return health_status 
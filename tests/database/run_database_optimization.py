#!/usr/bin/env python3
"""
Database Performance Optimization Script for Social Download Manager v2.0

This script provides comprehensive database optimization including:
- SQLite PRAGMA optimizations
- Query analysis and index recommendations
- Performance benchmarking and monitoring
- Query result caching optimization

Usage:
    python run_database_optimization.py --optimize-settings
    python run_database_optimization.py --analyze-queries
    python run_database_optimization.py --create-indexes
    python run_database_optimization.py --full-optimization
    python run_database_optimization.py --monitor-health
"""

import sys
import argparse
import time
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from scripts.performance.database_optimizer import DatabasePerformanceOptimizer, SQLiteOptimizer
    from scripts.performance.metrics import MetricsCollector
    from scripts.performance.reports import PerformanceReporter, ReportFormat, ReportConfig
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def find_database_file() -> Path:
    """Find the main database file"""
    possible_paths = [
        Path("test.db"),
        Path("data/social_download_manager.db"),
        Path("social_download_manager.db"),
        Path("downloads.db")
    ]
    
    for db_path in possible_paths:
        if db_path.exists():
            return db_path
    
    # If no database found, use test.db (will be created)
    return Path("test.db")


def optimize_database_settings(db_path: Path) -> bool:
    """Optimize database settings"""
    print("🔧 Optimizing Database Settings...")
    
    try:
        optimizer = SQLiteOptimizer(db_path)
        results = optimizer.optimize_database_settings()
        
        print(f"  📋 Applied settings to: {db_path}")
        
        success_count = sum(1 for setting in results.values() 
                          if isinstance(setting, dict) and setting.get('success', False))
        total_count = len([k for k in results.keys() if k != 'error'])
        
        print(f"  ✅ Successfully applied: {success_count}/{total_count} settings")
        
        # Show applied settings
        for setting, result in results.items():
            if isinstance(result, dict) and result.get('success'):
                print(f"    • {setting}: {result.get('applied')}")
            elif isinstance(result, dict) and not result.get('success'):
                print(f"    ❌ {setting}: {result.get('error')}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"  ❌ Database settings optimization failed: {e}")
        return False


def analyze_query_performance(db_path: Path) -> bool:
    """Analyze query performance and identify bottlenecks"""
    print("🔍 Analyzing Query Performance...")
    
    try:
        optimizer = DatabasePerformanceOptimizer(db_path)
        
        # Test common queries
        test_results = []
        total_missing_indexes = 0
        
        for query_name, query, params in optimizer.common_queries:
            try:
                print(f"  📊 Analyzing: {query_name}")
                analysis = optimizer.sqlite_optimizer.analyze_query_performance(query, params)
                
                print(f"    Complexity: {analysis.complexity_score}/10")
                print(f"    Uses indexes: {'Yes' if analysis.has_indexes else 'No'}")
                print(f"    Missing indexes: {len(analysis.missing_indexes)}")
                print(f"    Estimated cost: {analysis.estimated_cost:.1f}")
                
                if analysis.suggestions:
                    print("    Suggestions:")
                    for suggestion in analysis.suggestions[:2]:  # Show top 2
                        print(f"      • {suggestion}")
                
                test_results.append(analysis)
                total_missing_indexes += len(analysis.missing_indexes)
                
            except Exception as e:
                print(f"    ❌ Analysis failed: {e}")
        
        # Summary
        avg_complexity = sum(r.complexity_score for r in test_results) / max(len(test_results), 1)
        queries_with_indexes = sum(1 for r in test_results if r.has_indexes)
        
        print(f"\n  📈 Analysis Summary:")
        print(f"    Queries analyzed: {len(test_results)}")
        print(f"    Average complexity: {avg_complexity:.1f}/10")
        print(f"    Queries with indexes: {queries_with_indexes}/{len(test_results)}")
        print(f"    Total missing indexes: {total_missing_indexes}")
        
        return len(test_results) > 0
        
    except Exception as e:
        print(f"  ❌ Query analysis failed: {e}")
        return False


def create_recommended_indexes(db_path: Path) -> bool:
    """Create recommended indexes"""
    print("🏗️ Creating Recommended Indexes...")
    
    try:
        optimizer = DatabasePerformanceOptimizer(db_path)
        
        # Analyze queries to get recommendations
        query_analyses = []
        for query_name, query, params in optimizer.common_queries:
            try:
                analysis = optimizer.sqlite_optimizer.analyze_query_performance(query, params)
                query_analyses.append(analysis)
            except Exception as e:
                print(f"  ⚠️ Could not analyze '{query_name}': {e}")
        
        # Create indexes
        if query_analyses:
            results = optimizer.sqlite_optimizer.create_recommended_indexes(query_analyses)
            
            created = len(results.get('created_indexes', []))
            skipped = len(results.get('skipped_indexes', []))
            failed = len(results.get('failed_indexes', []))
            
            print(f"  📊 Index Creation Results:")
            print(f"    Created: {created}")
            print(f"    Skipped: {skipped}")
            print(f"    Failed: {failed}")
            
            # Show created indexes
            for index_info in results.get('created_indexes', []):
                print(f"    ✅ {index_info['name']} ({index_info['creation_time_ms']:.1f}ms)")
            
            # Show skipped indexes
            for index_info in results.get('skipped_indexes', []):
                print(f"    ⏭️ {index_info.get('sql', 'Unknown')}: {index_info.get('reason', 'Unknown')}")
            
            # Show failed indexes
            for index_info in results.get('failed_indexes', []):
                print(f"    ❌ Failed: {index_info.get('error', 'Unknown error')}")
            
            return created > 0 or skipped > 0
        else:
            print("  ⚠️ No query analyses available for index recommendations")
            return False
            
    except Exception as e:
        print(f"  ❌ Index creation failed: {e}")
        return False


def run_full_optimization(db_path: Path) -> bool:
    """Run comprehensive database optimization"""
    print("🚀 Running Comprehensive Database Optimization...")
    print("=" * 60)
    
    try:
        optimizer = DatabasePerformanceOptimizer(db_path)
        start_time = time.time()
        
        results = optimizer.run_comprehensive_optimization()
        
        duration = time.time() - start_time
        
        print(f"\n📊 Optimization Completed in {duration:.2f}s")
        print("=" * 60)
        
        # Show results summary
        optimization_steps = results.get('optimization_steps', {})
        
        # Database settings
        settings_result = optimization_steps.get('database_settings', {})
        if settings_result:
            success_count = sum(1 for v in settings_result.values() 
                              if isinstance(v, dict) and v.get('success', False))
            print(f"✅ Database Settings: {success_count} settings applied")
        
        # Query analysis
        query_analysis = optimization_steps.get('query_analysis', {})
        if query_analysis:
            print(f"🔍 Query Analysis: {query_analysis.get('total_queries_analyzed', 0)} queries analyzed")
            print(f"   Average complexity: {query_analysis.get('average_complexity', 0):.1f}/10")
            print(f"   Queries needing indexes: {query_analysis.get('queries_with_missing_indexes', 0)}")
        
        # Index creation
        index_creation = optimization_steps.get('index_creation', {})
        if index_creation:
            created = len(index_creation.get('created_indexes', []))
            skipped = len(index_creation.get('skipped_indexes', []))
            print(f"🏗️ Index Creation: {created} created, {skipped} skipped")
        
        # Performance improvements
        improvements = results.get('performance_improvements', {})
        if improvements:
            overall_improvement = improvements.get('overall_improvement_percent', 0)
            print(f"📈 Performance Improvement: {overall_improvement:.1f}%")
        
        # Recommendations
        recommendations = results.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for i, rec in enumerate(recommendations[:5], 1):  # Show top 5
                print(f"   {i}. {rec}")
        
        # Save detailed results
        results_file = Path("scripts/performance_results/database_optimization_results.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved: {results_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Full optimization failed: {e}")
        return False


def monitor_database_health(db_path: Path) -> bool:
    """Monitor database health and performance"""
    print("🏥 Monitoring Database Health...")
    
    try:
        optimizer = DatabasePerformanceOptimizer(db_path)
        health_status = optimizer.monitor_database_health()
        
        overall_health = health_status.get('overall_health', 'unknown')
        health_emoji = {
            'good': '✅',
            'warning': '⚠️',
            'critical': '❌'
        }.get(overall_health, '❓')
        
        print(f"  {health_emoji} Overall Health: {overall_health.upper()}")
        
        # Show metrics
        metrics = health_status.get('metrics', {})
        print(f"  📊 Database Metrics:")
        print(f"    Size: {metrics.get('database_size_mb', 0):.1f} MB")
        print(f"    Query count: {metrics.get('query_count', 0)}")
        print(f"    Average query time: {metrics.get('avg_query_time_ms', 0):.1f}ms")
        print(f"    Slow queries: {metrics.get('slow_query_count', 0)}")
        print(f"    Cache hit ratio: {metrics.get('cache_hit_ratio', 0):.1%}")
        
        # Show alerts
        alerts = health_status.get('alerts', [])
        if alerts:
            print(f"  🚨 Alerts ({len(alerts)}):")
            for alert in alerts:
                print(f"    • {alert}")
        else:
            print(f"  ✅ No alerts - database is healthy")
        
        # Generate performance report
        performance_report = optimizer.sqlite_optimizer.generate_performance_report()
        report_file = Path("scripts/performance_results/database_health_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(performance_report, f, indent=2, default=str)
        
        print(f"  📄 Health report saved: {report_file}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Health monitoring failed: {e}")
        return False


def benchmark_query_performance(db_path: Path) -> bool:
    """Benchmark query performance before and after optimization"""
    print("⏱️ Benchmarking Query Performance...")
    
    try:
        optimizer = DatabasePerformanceOptimizer(db_path)
        
        print("  🔄 Running performance benchmarks...")
        
        benchmark_results = {}
        total_time_before = 0
        total_time_after = 0
        
        for query_name, query, params in optimizer.common_queries[:5]:  # Test first 5 queries
            try:
                print(f"    📊 Benchmarking: {query_name}")
                
                # Benchmark without caching
                start_time = time.time()
                results, query_time = optimizer.sqlite_optimizer.execute_optimized_query(
                    query, params, use_cache=False
                )
                total_time = time.time() - start_time
                
                # Benchmark with caching
                start_time = time.time()
                cached_results, cached_query_time = optimizer.sqlite_optimizer.execute_optimized_query(
                    query, params, use_cache=True
                )
                cached_total_time = time.time() - start_time
                
                improvement = 0.0
                if total_time > 0:
                    improvement = ((total_time - cached_total_time) / total_time) * 100
                
                benchmark_results[query_name] = {
                    'without_cache_ms': total_time * 1000,
                    'with_cache_ms': cached_total_time * 1000,
                    'improvement_percent': improvement,
                    'result_count': len(results)
                }
                
                total_time_before += total_time
                total_time_after += cached_total_time
                
                print(f"      Without cache: {total_time*1000:.1f}ms")
                print(f"      With cache: {cached_total_time*1000:.1f}ms")
                print(f"      Improvement: {improvement:.1f}%")
                
            except Exception as e:
                print(f"      ❌ Benchmark failed: {e}")
        
        # Overall results
        overall_improvement = 0.0
        if total_time_before > 0:
            overall_improvement = ((total_time_before - total_time_after) / total_time_before) * 100
        
        print(f"\n  📈 Overall Performance:")
        print(f"    Total time before: {total_time_before*1000:.1f}ms")
        print(f"    Total time after: {total_time_after*1000:.1f}ms")
        print(f"    Overall improvement: {overall_improvement:.1f}%")
        
        # Save benchmark results
        benchmark_file = Path("scripts/performance_results/query_benchmark_results.json")
        benchmark_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(benchmark_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'overall_improvement_percent': overall_improvement,
                'total_time_before_ms': total_time_before * 1000,
                'total_time_after_ms': total_time_after * 1000,
                'query_results': benchmark_results
            }, f, indent=2)
        
        print(f"  📄 Benchmark results saved: {benchmark_file}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Performance benchmarking failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Database Performance Optimization for Social Download Manager v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_database_optimization.py --optimize-settings
  python run_database_optimization.py --full-optimization
  python run_database_optimization.py --monitor-health
  python run_database_optimization.py --benchmark
        """
    )
    
    parser.add_argument('--database', '-db', type=str, 
                       help='Path to database file (auto-detected if not specified)')
    parser.add_argument('--optimize-settings', action='store_true',
                       help='Optimize database settings and PRAGMA configurations')
    parser.add_argument('--analyze-queries', action='store_true',
                       help='Analyze query performance and identify bottlenecks')
    parser.add_argument('--create-indexes', action='store_true',
                       help='Create recommended indexes based on query analysis')
    parser.add_argument('--full-optimization', action='store_true',
                       help='Run comprehensive database optimization')
    parser.add_argument('--monitor-health', action='store_true',
                       help='Monitor database health and performance metrics')
    parser.add_argument('--benchmark', action='store_true',
                       help='Benchmark query performance')
    parser.add_argument('--all', action='store_true',
                       help='Run all optimization and monitoring operations')
    
    args = parser.parse_args()
    
    # Auto-detect database if not specified
    if args.database:
        db_path = Path(args.database)
    else:
        db_path = find_database_file()
    
    print("🚀 Social Download Manager v2.0 Database Optimization")
    print("=" * 60)
    print(f"📂 Database: {db_path}")
    print(f"📏 Size: {db_path.stat().st_size / (1024*1024):.1f} MB" if db_path.exists() else "📏 Size: New database")
    print("=" * 60)
    
    success = True
    
    try:
        if args.all or args.optimize_settings:
            success &= optimize_database_settings(db_path)
            print()
        
        if args.all or args.analyze_queries:
            success &= analyze_query_performance(db_path)
            print()
        
        if args.all or args.create_indexes:
            success &= create_recommended_indexes(db_path)
            print()
        
        if args.all or args.full_optimization:
            success &= run_full_optimization(db_path)
            print()
        
        if args.all or args.benchmark:
            success &= benchmark_query_performance(db_path)
            print()
        
        if args.all or args.monitor_health:
            success &= monitor_database_health(db_path)
            print()
        
        # If no specific operation specified, run full optimization
        if not any([args.optimize_settings, args.analyze_queries, args.create_indexes, 
                   args.full_optimization, args.monitor_health, args.benchmark, args.all]):
            print("No specific operation specified. Running full optimization...")
            print()
            success = run_full_optimization(db_path)
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        success = False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        success = False
    
    print("=" * 60)
    if success:
        print("✅ Database optimization completed successfully!")
    else:
        print("❌ Database optimization completed with errors")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 
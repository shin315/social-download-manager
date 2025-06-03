#!/usr/bin/env python3
"""
Minimal test for database optimization
"""

import sys
sys.path.insert(0, '.')

try:
    print("1. Importing optimizer...")
    from scripts.performance.database_optimizer import DatabasePerformanceOptimizer
    print("✅ Import successful")
    
    print("2. Creating optimizer instance...")
    optimizer = DatabasePerformanceOptimizer('test_optimization.db')
    print("✅ Instance created")
    
    print("3. Testing database connection...")
    import sqlite3
    conn = sqlite3.connect('test_optimization.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM content")
    count = cursor.fetchone()[0]
    print(f"✅ Database has {count} content records")
    conn.close()
    
    print("4. Testing SQLite optimizer settings...")
    settings_result = optimizer.sqlite_optimizer.optimize_database_settings()
    print(f"✅ Settings applied: {len([k for k, v in settings_result.items() if isinstance(v, dict) and v.get('success', False)])}")
    
    print("5. Testing single query analysis...")
    test_query = "SELECT * FROM content WHERE platform = ? LIMIT 5"
    analysis = optimizer.sqlite_optimizer.analyze_query_performance(test_query, ('youtube',))
    print(f"✅ Query analysis: complexity={analysis.complexity_score}, suggestions={len(analysis.suggestions)}")
    
    print("\n🎉 Basic components working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 
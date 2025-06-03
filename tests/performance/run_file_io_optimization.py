#!/usr/bin/env python3
"""
File I/O Optimization Test Runner
=================================

Comprehensive testing suite for Social Download Manager v2.0 file I/O optimizations.
Tests all aspects of file operations including chunking, disk management, validation,
and progress tracking.

Usage:
    python run_file_io_optimization.py [--mode=MODE] [--cleanup]

Modes:
    all      - Run all optimization tests (default)
    chunk    - Test chunk size optimization only
    disk     - Test disk space management only  
    atomic   - Test atomic file operations only
    validate - Test file validation only
    progress - Test progress tracking only
    demo     - Run interactive demonstration
"""

import os
import sys
import time
import asyncio
import argparse
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, List, Any

# Add scripts directory to path for imports
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts', 'performance')
sys.path.insert(0, scripts_dir)

try:
    from file_io_optimizer import (
        FileIOOptimizer, FileIOBenchmark, ChunkSizeOptimizer,
        DiskSpaceManager, OptimizedFileWriter, FileValidator,
        ProgressTracker, FileIOMetrics
    )
except ImportError as e:
    print(f"❌ Error importing file I/O optimizer: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install aiofiles")
    sys.exit(1)

class FileIOTestRunner:
    """Comprehensive file I/O optimization test runner."""
    
    def __init__(self):
        self.test_dir = os.path.join(tempfile.gettempdir(), "fileio_test")
        self.optimizer = None
        self.results = {}
        
    def setup(self):
        """Setup test environment."""
        print("🔧 Setting up File I/O test environment...")
        
        # Create test directory
        os.makedirs(self.test_dir, exist_ok=True)
        
        # Initialize optimizer
        self.optimizer = FileIOOptimizer(temp_dir=self.test_dir)
        
        print(f"✅ Test environment ready: {self.test_dir}")
    
    def cleanup(self):
        """Clean up test environment."""
        print("🧹 Cleaning up test environment...")
        try:
            import shutil
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def test_chunk_optimization(self) -> Dict[str, Any]:
        """Test chunk size optimization."""
        print("\n📦 Phase 1: Chunk Size Optimization")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            chunk_optimizer = ChunkSizeOptimizer()
            
            # Test different file sizes
            test_cases = [
                (500 * 1024, 25.0),      # 500KB, slow disk
                (5 * 1024 * 1024, 50.0), # 5MB, medium disk
                (50 * 1024 * 1024, 100.0), # 50MB, fast SSD
                (500 * 1024 * 1024, 200.0) # 500MB, very fast SSD
            ]
            
            for file_size, disk_speed in test_cases:
                chunk_size = chunk_optimizer.get_optimal_chunk_size(file_size, disk_speed)
                size_mb = file_size // (1024 * 1024)
                chunk_kb = chunk_size // 1024
                
                print(f"  File: {size_mb}MB, Disk: {disk_speed}MB/s → Chunk: {chunk_kb}KB")
                
                # Validate chunk size is reasonable
                if not (8 <= chunk_kb <= 16 * 1024):
                    results["errors"].append(f"Invalid chunk size: {chunk_kb}KB")
                    
                results["details"][f"{size_mb}MB"] = {
                    "chunk_size_kb": chunk_kb,
                    "disk_speed": disk_speed
                }
            
            # Test performance history update
            chunk_optimizer.update_performance(1024 * 1024, 75.5)
            if 1024 * 1024 not in chunk_optimizer.performance_history:
                results["errors"].append("Performance history not updated")
            
            print(f"✅ Chunk optimization tests: {len(results['details'])} cases tested")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Chunk optimization failed: {e}")
        
        return results
    
    async def test_disk_space_management(self) -> Dict[str, Any]:
        """Test disk space management."""
        print("\n💾 Phase 2: Disk Space Management")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            disk_manager = DiskSpaceManager(min_free_space_mb=100)
            
            # Test disk space info
            disk_info = disk_manager.get_disk_space_info(self.test_dir)
            print(f"  Total Space: {disk_info.total // (1024**3):.1f} GB")
            print(f"  Free Space: {disk_info.free // (1024**3):.1f} GB")
            print(f"  Usage: {disk_info.usage_percentage:.1f}%")
            
            results["details"]["disk_info"] = {
                "total_gb": disk_info.total // (1024**3),
                "free_gb": disk_info.free // (1024**3),
                "usage_percent": disk_info.usage_percentage
            }
            
            # Test sufficient space check
            small_file = 1024 * 1024  # 1MB
            has_space = disk_manager.has_sufficient_space(self.test_dir, small_file)
            print(f"  Space check for 1MB: {'✅' if has_space else '❌'}")
            
            if not has_space and disk_info.free > 200 * 1024 * 1024:  # 200MB
                results["errors"].append("Space check failed despite sufficient space")
            
            # Test temp file cleanup
            # Create test temp files
            temp_files = []
            for i in range(3):
                temp_file = os.path.join(self.test_dir, f"temp_test_{i}.tmp")
                with open(temp_file, 'w') as f:
                    f.write("test data" * 100)
                temp_files.append(temp_file)
                
                # Make files appear old by adjusting modification time
                old_time = time.time() - (25 * 3600)  # 25 hours ago
                os.utime(temp_file, (old_time, old_time))
            
            cleaned_bytes = disk_manager.cleanup_temp_files(self.test_dir, max_age_hours=24)
            print(f"  Cleaned up: {cleaned_bytes} bytes")
            
            # Verify files were cleaned
            remaining_files = [f for f in temp_files if os.path.exists(f)]
            if remaining_files:
                results["errors"].append(f"Temp files not cleaned: {len(remaining_files)}")
            else:
                print(f"  ✅ All {len(temp_files)} temp files cleaned successfully")
            
            results["details"]["cleanup"] = {
                "cleaned_bytes": cleaned_bytes,
                "files_cleaned": len(temp_files) - len(remaining_files)
            }
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Disk space management failed: {e}")
        
        return results
    
    async def test_atomic_operations(self) -> Dict[str, Any]:
        """Test atomic file operations."""
        print("\n⚛️ Phase 3: Atomic File Operations")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            file_writer = OptimizedFileWriter(
                ChunkSizeOptimizer(), 
                DiskSpaceManager()
            )
            
            # Test atomic write success
            test_file = os.path.join(self.test_dir, "atomic_test.bin")
            test_data = b"Hello, atomic world!" * 1000
            
            async def test_data_stream():
                chunk_size = 1024
                for i in range(0, len(test_data), chunk_size):
                    yield test_data[i:i + chunk_size]
                    await asyncio.sleep(0.001)
            
            success = await file_writer.write_chunked(
                test_file, test_data_stream(), len(test_data)
            )
            
            if success and os.path.exists(test_file):
                # Verify file content
                with open(test_file, 'rb') as f:
                    written_data = f.read()
                
                if written_data == test_data:
                    print(f"  ✅ Atomic write successful: {len(test_data)} bytes")
                    results["details"]["write_success"] = True
                else:
                    results["errors"].append("Written data doesn't match expected")
            else:
                results["errors"].append("Atomic write failed")
            
            # Test atomic write with simulated failure
            failed_file = os.path.join(self.test_dir, "atomic_fail_test.bin")
            
            try:
                async with file_writer.atomic_write(failed_file, len(test_data)) as f:
                    await f.write(test_data[:100])
                    # Simulate failure
                    raise Exception("Simulated failure")
            except:
                pass  # Expected to fail
            
            # Verify no partial file exists
            if not os.path.exists(failed_file):
                print(f"  ✅ Atomic write cleanup on failure")
                results["details"]["failure_cleanup"] = True
            else:
                results["errors"].append("Partial file not cleaned up on failure")
            
            # Test disk space check
            huge_file = os.path.join(self.test_dir, "huge_test.bin")
            huge_size = 1024 * 1024 * 1024 * 1024  # 1TB (should fail)
            
            try:
                async with file_writer.atomic_write(huge_file, huge_size) as f:
                    await f.write(b"test")
                results["errors"].append("Should have failed due to insufficient space")
            except IOError:
                print(f"  ✅ Disk space check working")
                results["details"]["space_check"] = True
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Atomic operations failed: {e}")
        
        return results
    
    async def test_file_validation(self) -> Dict[str, Any]:
        """Test file validation."""
        print("\n🔍 Phase 4: File Validation")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            validator = FileValidator()
            
            # Create test file with known content
            test_file = os.path.join(self.test_dir, "validation_test.bin")
            test_data = b"Validation test data!" * 500
            
            with open(test_file, 'wb') as f:
                f.write(test_data)
            
            # Calculate expected hash
            expected_hash = hashlib.sha256(test_data).hexdigest()
            
            # Test hash validation
            start_time = time.time()
            is_valid = await validator.validate_file_hash(test_file, expected_hash)
            validation_time = time.time() - start_time
            
            if is_valid:
                print(f"  ✅ Hash validation passed ({validation_time:.3f}s)")
                results["details"]["hash_validation"] = {
                    "success": True,
                    "time_seconds": validation_time
                }
            else:
                results["errors"].append("Hash validation failed")
            
            # Test invalid hash
            wrong_hash = "0" * 64  # Invalid SHA256
            is_invalid = await validator.validate_file_hash(test_file, wrong_hash)
            
            if not is_invalid:
                print(f"  ✅ Invalid hash correctly rejected")
                results["details"]["invalid_hash_rejection"] = True
            else:
                results["errors"].append("Invalid hash incorrectly accepted")
            
            # Test size validation
            expected_size = len(test_data)
            size_valid = validator.validate_file_size(test_file, expected_size)
            
            if size_valid:
                print(f"  ✅ Size validation passed ({expected_size} bytes)")
                results["details"]["size_validation"] = True
            else:
                results["errors"].append("Size validation failed")
            
            # Test wrong size
            wrong_size = expected_size + 100
            size_invalid = validator.validate_file_size(test_file, wrong_size)
            
            if not size_invalid:
                print(f"  ✅ Wrong size correctly rejected")
                results["details"]["wrong_size_rejection"] = True
            else:
                results["errors"].append("Wrong size incorrectly accepted")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ File validation failed: {e}")
        
        return results
    
    async def test_progress_tracking(self) -> Dict[str, Any]:
        """Test progress tracking."""
        print("\n📊 Phase 5: Progress Tracking")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Test progress tracker
            progress_updates = []
            
            def capture_progress(bytes_processed, total_bytes, percent):
                progress_updates.append({
                    "bytes": bytes_processed,
                    "total": total_bytes,
                    "percent": percent
                })
            
            tracker = ProgressTracker(update_interval=0.05)  # 50ms updates
            tracker.add_callback(capture_progress)
            
            # Simulate progress updates
            total_size = 1000000  # 1MB
            chunk_size = 10000    # 10KB chunks
            
            for i in range(0, total_size, chunk_size):
                bytes_processed = min(i + chunk_size, total_size)
                tracker.update_progress(bytes_processed, total_size)
                await asyncio.sleep(0.01)  # Simulate processing time
            
            if progress_updates:
                final_update = progress_updates[-1]
                print(f"  ✅ Progress tracking: {len(progress_updates)} updates")
                print(f"  Final: {final_update['percent']:.1f}% ({final_update['bytes']} bytes)")
                
                results["details"]["progress_tracking"] = {
                    "updates_count": len(progress_updates),
                    "final_percent": final_update["percent"],
                    "final_bytes": final_update["bytes"]
                }
                
                # Verify progress makes sense
                if final_update["percent"] != 100.0:
                    results["errors"].append("Final progress not 100%")
                    
                if final_update["bytes"] != total_size:
                    results["errors"].append("Final bytes don't match total")
            else:
                results["errors"].append("No progress updates captured")
            
            # Test throttling
            rapid_updates = []
            
            def capture_rapid(bytes_processed, total_bytes, percent):
                rapid_updates.append(time.time())
            
            rapid_tracker = ProgressTracker(update_interval=0.1)  # 100ms throttle
            rapid_tracker.add_callback(capture_rapid)
            
            # Rapid fire updates
            for i in range(10):
                rapid_tracker.update_progress(i * 1000, 10000)
                await asyncio.sleep(0.02)  # 20ms intervals (faster than throttle)
            
            # Should have fewer updates due to throttling
            if len(rapid_updates) < 8:  # Less than the 10 attempts
                print(f"  ✅ Progress throttling working: {len(rapid_updates)} updates")
                results["details"]["throttling"] = True
            else:
                results["errors"].append("Progress throttling not working")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Progress tracking failed: {e}")
        
        return results
    
    async def test_integrated_performance(self) -> Dict[str, Any]:
        """Test integrated file I/O performance."""
        print("\n🚀 Phase 6: Integrated Performance Test")
        print("-" * 40)
        
        results = {"status": "PASSED", "details": {}, "errors": []}
        
        try:
            # Test different file sizes
            test_sizes = [
                100 * 1024,      # 100KB
                1 * 1024 * 1024, # 1MB  
                10 * 1024 * 1024 # 10MB
            ]
            
            benchmark = FileIOBenchmark(self.optimizer)
            
            # Benchmark write speeds
            write_speeds = await benchmark.benchmark_write_speeds(test_sizes)
            print(f"  Write Performance:")
            for size, speed in write_speeds.items():
                print(f"    {size}: {speed:.1f} MB/s")
            
            results["details"]["write_speeds"] = write_speeds
            
            # Benchmark validation speeds
            validation_speeds = await benchmark.benchmark_validation_speeds(test_sizes)
            print(f"  Validation Performance:")
            for size, speed in validation_speeds.items():
                print(f"    {size}: {speed:.1f} MB/s")
            
            results["details"]["validation_speeds"] = validation_speeds
            
            # Test full download simulation
            test_file = os.path.join(self.test_dir, "performance_test.bin")
            file_size = 5 * 1024 * 1024  # 5MB
            
            # Create expected hash for validation
            test_content = b"Performance test data! " * (file_size // 24)
            expected_hash = hashlib.sha256(test_content).hexdigest()
            
            download_start = time.time()
            
            # Mock download with progress tracking
            progress_updates = []
            def track_progress(processed, total, percent):
                progress_updates.append(percent)
            
            # Use real download method but with mock data
            async def mock_download_stream():
                chunk_size = 64 * 1024  # 64KB chunks
                for i in range(0, len(test_content), chunk_size):
                    chunk = test_content[i:i + chunk_size]
                    yield chunk
                    await asyncio.sleep(0.001)  # Simulate network
            
            # Perform optimized download
            success = await self.optimizer.file_writer.write_chunked(
                test_file, mock_download_stream(), file_size, track_progress
            )
            
            download_time = time.time() - download_start
            
            if success:
                # Validate the download
                is_valid = await self.optimizer.file_validator.validate_file_hash(
                    test_file, expected_hash
                )
                
                download_speed = (file_size / download_time) / (1024 * 1024)  # MB/s
                
                print(f"  ✅ Integrated test: {download_speed:.1f} MB/s")
                print(f"  Validation: {'✅ PASS' if is_valid else '❌ FAIL'}")
                print(f"  Progress updates: {len(progress_updates)}")
                
                results["details"]["integrated_test"] = {
                    "success": True,
                    "speed_mbps": download_speed,
                    "validation_passed": is_valid,
                    "progress_updates": len(progress_updates)
                }
                
                if not is_valid:
                    results["errors"].append("Integrated validation failed")
                    
            else:
                results["errors"].append("Integrated download failed")
            
        except Exception as e:
            results["status"] = "FAILED"
            results["errors"].append(str(e))
            print(f"❌ Integrated performance test failed: {e}")
        
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all file I/O optimization tests."""
        print("🔥 Starting File I/O Optimization Tests")
        print("=" * 50)
        
        all_results = {}
        
        # Run all test phases
        test_phases = [
            ("chunk_optimization", self.test_chunk_optimization),
            ("disk_space_management", self.test_disk_space_management), 
            ("atomic_operations", self.test_atomic_operations),
            ("file_validation", self.test_file_validation),
            ("progress_tracking", self.test_progress_tracking),
            ("integrated_performance", self.test_integrated_performance)
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
        
        # Summary
        print(f"\n📋 File I/O Optimization Test Summary")
        print("=" * 50)
        print(f"✅ Passed: {passed_count}/{len(test_phases)} phases")
        
        if passed_count == len(test_phases):
            print("🎉 ALL FILE I/O TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - check details above")
        
        # Show metrics
        if self.optimizer:
            metrics = self.optimizer.get_metrics()
            print(f"\n📊 Final Metrics:")
            print(f"  Total Downloads: {metrics.total_downloads}")
            print(f"  Failed Operations: {metrics.failed_operations}")
            print(f"  Temp Files: {metrics.temp_files_count}")
            print(f"  Validation Time: {metrics.validation_time:.3f}s")
        
        return all_results

async def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="File I/O Optimization Test Runner")
    parser.add_argument("--mode", choices=["all", "chunk", "disk", "atomic", "validate", "progress", "demo"], 
                       default="all", help="Test mode to run")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test files after running")
    
    args = parser.parse_args()
    
    runner = FileIOTestRunner()
    
    try:
        runner.setup()
        
        if args.mode == "demo":
            # Run demo from the module
            from file_io_optimizer import demo_file_io_optimization
            demo_file_io_optimization()
        else:
            # Run tests based on mode
            if args.mode == "all":
                await runner.run_all_tests()
            elif args.mode == "chunk":
                await runner.test_chunk_optimization()
            elif args.mode == "disk":
                await runner.test_disk_space_management()
            elif args.mode == "atomic":
                await runner.test_atomic_operations()
            elif args.mode == "validate":
                await runner.test_file_validation()
            elif args.mode == "progress":
                await runner.test_progress_tracking()
        
    finally:
        if args.cleanup:
            runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 
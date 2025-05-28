"""
App Controller Usage Examples

This module contains practical examples of how to use the App Controller
in various scenarios within the Social Download Manager application.
"""

import asyncio
import threading
import time
from typing import Optional, Dict, Any

from core.app_controller import get_app_controller, initialize_app_controller
from core.event_system import EventHandler, Event, EventType
from core.services import ContentDTO, AnalyticsDTO


# Example 1: Basic Application Setup
class BasicApplicationExample:
    """Example of basic application setup with controller"""
    
    def __init__(self):
        self.controller = None
    
    def initialize_application(self) -> bool:
        """Initialize the application with controller"""
        print("Initializing Social Download Manager...")
        
        # Initialize controller
        success = initialize_app_controller()
        if not success:
            print("❌ Failed to initialize app controller")
            return False
        
        # Get controller instance
        self.controller = get_app_controller()
        
        # Verify controller state
        status = self.controller.get_status()
        print(f"✅ Controller initialized - State: {status.state}")
        print(f"📦 Components: {status.components_initialized}")
        print(f"🔧 Services: {status.services_registered}")
        
        return True
    
    def shutdown_application(self) -> bool:
        """Gracefully shutdown the application"""
        if self.controller:
            print("Shutting down application...")
            success = self.controller.shutdown()
            if success:
                print("✅ Application shut down successfully")
            else:
                print("❌ Shutdown encountered errors")
            return success
        return True


# Example 2: UI Component Integration
class UIComponentExample(EventHandler):
    """Example UI component that integrates with the controller"""
    
    def __init__(self, name: str):
        self.name = name
        self.controller = get_app_controller()
        self.downloads = {}
        self.messages = []
        
        # Register with controller
        self.controller.register_component(f"ui_{name}", self)
        
        # Subscribe to events
        event_bus = self.controller.get_event_bus()
        if event_bus:
            event_bus.add_handler(self)
            print(f"📺 UI Component '{name}' registered for events")
    
    def handle_event(self, event: Event):
        """Handle events from the controller"""
        if event.event_type == EventType.DOWNLOAD_STARTED:
            self.on_download_started(event.data)
        elif event.event_type == EventType.DOWNLOAD_COMPLETED:
            self.on_download_completed(event.data)
        elif event.event_type == EventType.ERROR_OCCURRED:
            self.on_error_occurred(event.data)
        elif event.event_type == EventType.CONFIG_CHANGED:
            self.on_config_changed(event.data)
    
    def on_download_started(self, data: Dict[str, Any]):
        """Handle download started event"""
        download_id = data.get('content_id', 'unknown')
        url = data.get('url', 'unknown')
        self.downloads[download_id] = {'url': url, 'status': 'downloading'}
        self.add_message(f"📥 Download started: {url[:50]}...")
    
    def on_download_completed(self, data: Dict[str, Any]):
        """Handle download completed event"""
        download_id = data.get('content_id', 'unknown')
        if download_id in self.downloads:
            self.downloads[download_id]['status'] = 'completed'
        self.add_message(f"✅ Download completed: {download_id}")
    
    def on_error_occurred(self, data: Dict[str, Any]):
        """Handle error event"""
        error_msg = data.get('error_message', 'Unknown error')
        context = data.get('context', 'unknown')
        self.add_message(f"❌ Error in {context}: {error_msg}")
    
    def on_config_changed(self, data: Dict[str, Any]):
        """Handle configuration change event"""
        self.add_message("⚙️ Configuration changed, reloading settings...")
    
    def add_message(self, message: str):
        """Add message to UI"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.messages.append(formatted_message)
        print(f"UI({self.name}): {formatted_message}")
    
    def show_status(self):
        """Display current status"""
        print(f"\n📊 UI Component '{self.name}' Status:")
        print(f"   Downloads: {len(self.downloads)}")
        print(f"   Messages: {len(self.messages)}")
        
        if self.downloads:
            print("   Active Downloads:")
            for download_id, info in self.downloads.items():
                print(f"     {download_id}: {info['status']} - {info['url'][:40]}...")
    
    def cleanup(self):
        """Cleanup when component is removed"""
        # Remove from event system
        event_bus = self.controller.get_event_bus()
        if event_bus:
            event_bus.remove_handler(self)
        
        # Unregister from controller
        self.controller.unregister_component(f"ui_{self.name}")
        print(f"🧹 UI Component '{self.name}' cleaned up")


# Example 3: Service Integration
class ServiceIntegrationExample:
    """Example of integrating with services through the controller"""
    
    def __init__(self):
        self.controller = get_app_controller()
    
    async def download_multiple_videos(self, urls: list) -> Dict[str, Any]:
        """Download multiple videos using controller services"""
        results = {
            'successful': [],
            'failed': [],
            'total': len(urls)
        }
        
        print(f"🚀 Starting download of {len(urls)} videos...")
        
        for i, url in enumerate(urls, 1):
            print(f"📥 Processing video {i}/{len(urls)}: {url[:50]}...")
            
            try:
                # Create content from URL
                content = await self.controller.create_content_from_url(url)
                if content:
                    print(f"✅ Content created: {content.id}")
                    
                    # Start download with options
                    download_options = {
                        "quality": "best",
                        "format": "mp4",
                        "output_dir": "./downloads"
                    }
                    
                    download_result = await self.controller.start_download(
                        url, options=download_options
                    )
                    
                    if download_result:
                        results['successful'].append({
                            'url': url,
                            'content_id': content.id,
                            'title': getattr(content, 'title', 'Unknown')
                        })
                    else:
                        results['failed'].append({'url': url, 'reason': 'Download failed'})
                else:
                    results['failed'].append({'url': url, 'reason': 'Content creation failed'})
                    
            except Exception as e:
                print(f"❌ Error processing {url}: {e}")
                results['failed'].append({'url': url, 'reason': str(e)})
        
        # Show results
        success_rate = len(results['successful']) / results['total'] * 100
        print(f"\n📊 Download Results:")
        print(f"   ✅ Successful: {len(results['successful'])}")
        print(f"   ❌ Failed: {len(results['failed'])}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        
        return results
    
    async def get_analytics_report(self) -> Optional[Dict[str, Any]]:
        """Get comprehensive analytics report"""
        print("📊 Generating analytics report...")
        
        analytics = await self.controller.get_analytics_overview()
        if analytics:
            report = {
                'total_downloads': getattr(analytics, 'total_downloads', 0),
                'success_rate': getattr(analytics, 'success_rate', 0),
                'avg_download_time': getattr(analytics, 'avg_download_time', 0),
                'popular_platforms': getattr(analytics, 'popular_platforms', []),
                'generated_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print("📈 Analytics Report:")
            for key, value in report.items():
                print(f"   {key}: {value}")
            
            return report
        else:
            print("❌ Failed to get analytics data")
            return None


# Example 4: Custom Component with Event Publishing
class CustomDownloadTrackerComponent(EventHandler):
    """Custom component that tracks downloads and publishes custom events"""
    
    def __init__(self):
        self.controller = get_app_controller()
        self.download_stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'in_progress': 0
        }
        
        # Register with controller
        self.controller.register_component("download_tracker", self)
        
        # Subscribe to events
        event_bus = self.controller.get_event_bus()
        if event_bus:
            event_bus.add_handler(self)
    
    def handle_event(self, event: Event):
        """Track download-related events"""
        if event.event_type == EventType.DOWNLOAD_STARTED:
            self.download_stats['total'] += 1
            self.download_stats['in_progress'] += 1
            self.check_milestones()
            
        elif event.event_type == EventType.DOWNLOAD_COMPLETED:
            self.download_stats['successful'] += 1
            self.download_stats['in_progress'] -= 1
            self.check_milestones()
            
        elif event.event_type == EventType.DOWNLOAD_FAILED:
            self.download_stats['failed'] += 1
            self.download_stats['in_progress'] -= 1
    
    def check_milestones(self):
        """Check for milestone achievements and publish events"""
        total = self.download_stats['total']
        
        # Check for milestone achievements
        milestones = [10, 50, 100, 500, 1000]
        for milestone in milestones:
            if total == milestone:
                self.publish_milestone_event(milestone)
    
    def publish_milestone_event(self, milestone: int):
        """Publish milestone achievement event"""
        event_bus = self.controller.get_event_bus()
        if event_bus:
            # Create custom milestone event
            event = Event(
                EventType.CUSTOM_EVENT,  # Assuming this exists or using existing type
                {
                    'event_subtype': 'milestone_achieved',
                    'milestone': milestone,
                    'total_downloads': self.download_stats['total'],
                    'success_rate': self.calculate_success_rate(),
                    'timestamp': time.time()
                }
            )
            event_bus.publish(event)
            print(f"🎉 Milestone achieved: {milestone} downloads!")
    
    def calculate_success_rate(self) -> float:
        """Calculate current success rate"""
        total_completed = self.download_stats['successful'] + self.download_stats['failed']
        if total_completed > 0:
            return (self.download_stats['successful'] / total_completed) * 100
        return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current download statistics"""
        return {
            **self.download_stats,
            'success_rate': self.calculate_success_rate()
        }
    
    def cleanup(self):
        """Cleanup when component is removed"""
        event_bus = self.controller.get_event_bus()
        if event_bus:
            event_bus.remove_handler(self)
        print("🧹 Download tracker cleaned up")


# Example 5: Error Handling Patterns
class ErrorHandlingExample:
    """Example of various error handling patterns with the controller"""
    
    def __init__(self):
        self.controller = get_app_controller()
        self.setup_error_handlers()
    
    def setup_error_handlers(self):
        """Setup custom error handlers"""
        
        def ui_notification_handler(error: Exception, context: str):
            """Handler for UI notifications"""
            print(f"🚨 UI Notification: Error in {context} - {str(error)[:100]}")
            # In real app, this would show a notification to user
        
        def detailed_logging_handler(error: Exception, context: str):
            """Handler for detailed logging"""
            print(f"📝 Detailed Log: Context={context}, Error={type(error).__name__}: {error}")
            # In real app, this would write to log file
        
        def metrics_handler(error: Exception, context: str):
            """Handler for error metrics collection"""
            print(f"📊 Metrics: Error recorded for context '{context}'")
            # In real app, this would send to analytics service
        
        # Register error handlers
        self.controller.add_error_handler(ui_notification_handler)
        self.controller.add_error_handler(detailed_logging_handler)
        self.controller.add_error_handler(metrics_handler)
        
        print("✅ Error handlers registered")
    
    async def demonstrate_error_scenarios(self):
        """Demonstrate various error handling scenarios"""
        print("\n🧪 Demonstrating error handling scenarios...\n")
        
        # Scenario 1: Service unavailable
        try:
            content_service = self.controller.get_content_service()
            if not content_service:
                raise RuntimeError("Content service not available")
        except Exception as e:
            self.controller.handle_error(e, "service_availability_check")
        
        # Scenario 2: Invalid URL
        try:
            invalid_url = "not-a-valid-url"
            content = await self.controller.create_content_from_url(invalid_url)
            if not content:
                raise ValueError(f"Failed to create content from URL: {invalid_url}")
        except Exception as e:
            self.controller.handle_error(e, "invalid_url_processing")
        
        # Scenario 3: Network timeout simulation
        try:
            # Simulate network timeout
            raise TimeoutError("Network request timed out after 30 seconds")
        except Exception as e:
            self.controller.handle_error(e, "network_timeout")
        
        print("✅ Error scenarios completed\n")


# Example 6: Multi-threaded Usage
class MultiThreadedExample:
    """Example of using controller in multi-threaded environment"""
    
    def __init__(self):
        self.controller = get_app_controller()
        self.results = {}
        self.lock = threading.Lock()
    
    def worker_thread(self, thread_id: int, urls: list):
        """Worker thread that processes URLs"""
        print(f"🧵 Thread {thread_id} starting with {len(urls)} URLs")
        
        thread_results = {
            'thread_id': thread_id,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'urls': urls
        }
        
        for url in urls:
            try:
                # Use controller in thread-safe manner
                event_bus = self.controller.get_event_bus()
                if event_bus:
                    # Publish processing start event
                    event = Event(
                        EventType.CUSTOM_EVENT,
                        {
                            'event_subtype': 'url_processing_started',
                            'thread_id': thread_id,
                            'url': url
                        }
                    )
                    event_bus.publish(event)
                
                # Simulate processing
                time.sleep(0.1)  # Simulate work
                
                thread_results['processed'] += 1
                thread_results['successful'] += 1
                
                print(f"✅ Thread {thread_id}: Processed {url[:30]}...")
                
            except Exception as e:
                thread_results['failed'] += 1
                self.controller.handle_error(e, f"thread_{thread_id}_processing")
        
        # Store results thread-safely
        with self.lock:
            self.results[thread_id] = thread_results
        
        print(f"🏁 Thread {thread_id} completed: {thread_results['successful']}/{thread_results['processed']} successful")
    
    def run_multi_threaded_processing(self, all_urls: list, num_threads: int = 3):
        """Run multi-threaded URL processing"""
        print(f"🚀 Starting multi-threaded processing with {num_threads} threads")
        
        # Split URLs among threads
        urls_per_thread = len(all_urls) // num_threads
        threads = []
        
        for i in range(num_threads):
            start_idx = i * urls_per_thread
            end_idx = start_idx + urls_per_thread if i < num_threads - 1 else len(all_urls)
            thread_urls = all_urls[start_idx:end_idx]
            
            thread = threading.Thread(
                target=self.worker_thread,
                args=(i + 1, thread_urls)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Print summary
        self.print_threading_summary()
    
    def print_threading_summary(self):
        """Print summary of multi-threaded processing"""
        print("\n📊 Multi-threading Summary:")
        total_processed = sum(r['processed'] for r in self.results.values())
        total_successful = sum(r['successful'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        
        print(f"   Total URLs processed: {total_processed}")
        print(f"   Successful: {total_successful}")
        print(f"   Failed: {total_failed}")
        print(f"   Success rate: {(total_successful/total_processed*100):.1f}%")
        
        for thread_id, results in self.results.items():
            print(f"   Thread {thread_id}: {results['successful']}/{results['processed']} successful")


# Example 7: Complete Application Workflow
async def complete_workflow_example():
    """Complete workflow example demonstrating full controller usage"""
    print("🎬 Starting complete workflow example...")
    
    # Step 1: Initialize application
    app = BasicApplicationExample()
    if not app.initialize_application():
        return
    
    try:
        # Step 2: Create UI components
        main_ui = UIComponentExample("main_window")
        progress_ui = UIComponentExample("progress_dialog")
        
        # Step 3: Add custom tracking component
        tracker = CustomDownloadTrackerComponent()
        
        # Step 4: Setup error handling
        error_handler = ErrorHandlingExample()
        
        # Step 5: Simulate some download operations
        service_example = ServiceIntegrationExample()
        
        # Sample URLs for testing
        test_urls = [
            "https://www.tiktok.com/@user/video/1",
            "https://youtube.com/watch?v=test1",
            "https://instagram.com/p/test1",
        ]
        
        # Download videos
        download_results = await service_example.download_multiple_videos(test_urls)
        
        # Step 6: Get analytics
        analytics_report = await service_example.get_analytics_report()
        
        # Step 7: Show component status
        main_ui.show_status()
        progress_ui.show_status()
        
        tracker_stats = tracker.get_stats()
        print(f"\n📊 Tracker Stats: {tracker_stats}")
        
        # Step 8: Demonstrate error handling
        await error_handler.demonstrate_error_scenarios()
        
        # Step 9: Demonstrate multi-threading
        mt_example = MultiThreadedExample()
        mt_urls = [f"https://example.com/video/{i}" for i in range(10)]
        mt_example.run_multi_threaded_processing(mt_urls, num_threads=3)
        
        print("✅ Complete workflow example finished successfully!")
        
    finally:
        # Step 10: Cleanup
        print("\n🧹 Cleaning up...")
        
        # Clean up components
        if 'main_ui' in locals():
            main_ui.cleanup()
        if 'progress_ui' in locals():
            progress_ui.cleanup()
        if 'tracker' in locals():
            tracker.cleanup()
        
        # Shutdown application
        app.shutdown_application()


# Main execution
if __name__ == "__main__":
    print("🚀 Social Download Manager - App Controller Examples")
    print("=" * 60)
    
    # Run the complete workflow example
    asyncio.run(complete_workflow_example()) 
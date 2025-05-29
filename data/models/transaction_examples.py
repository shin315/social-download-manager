"""
Transaction Usage Examples for Social Download Manager v2.0

Demonstrates various patterns for using transaction-aware repositories
including unit of work, bulk operations, and complex transactions.
"""

from typing import List
import logging

from .base import EntityId
from .downloads import DownloadModel, DownloadSession, DownloadError, DownloadStatus
from .download_repositories import (
    get_download_repository, get_download_session_repository, get_download_error_repository
)
from .transaction_repository import UnitOfWork, transactional
from ..database import TransactionIsolationLevel, TransactionPropagation


def example_simple_transaction():
    """Example: Simple transaction with auto-commit"""
    download_repo = get_download_repository()
    
    # Create a new download
    download = DownloadModel(
        content_id="test-content-001",
        url="https://example.com/video.mp4",
        status=DownloadStatus.QUEUED,
        file_path="/downloads/video.mp4"
    )
    
    # Save with automatic transaction
    saved_download = download_repo.save_transactional(download)
    print(f"Saved download with ID: {saved_download.id}")


def example_manual_transaction():
    """Example: Manual transaction management"""
    download_repo = get_download_repository()
    session_repo = get_download_session_repository()
    
    # Manual transaction
    with download_repo.transaction() as trans:
        # Create download
        download = DownloadModel(
            content_id="test-content-002",
            url="https://example.com/video2.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/video2.mp4"
        )
        saved_download = download_repo.save(download)
        
        # Create session
        session = DownloadSession(
            content_id=saved_download.content_id,
            download_id=saved_download.id,
            status=DownloadStatus.STARTING,
            downloader_type="youtube-dl"
        )
        saved_session = session_repo.save(session)
        
        print(f"Created download {saved_download.id} and session {saved_session.id}")
        # Transaction commits automatically on exit


def example_rollback_on_error():
    """Example: Transaction rollback on error"""
    download_repo = get_download_repository()
    session_repo = get_download_session_repository()
    
    try:
        with download_repo.transaction() as trans:
            # Create download
            download = DownloadModel(
                content_id="test-content-003",
                url="https://example.com/video3.mp4",
                status=DownloadStatus.QUEUED,
                file_path="/downloads/video3.mp4"
            )
            saved_download = download_repo.save(download)
            
            # Simulate error
            raise Exception("Simulated error during session creation")
            
            # This won't execute due to exception
            session = DownloadSession(
                content_id=saved_download.content_id,
                download_id=saved_download.id,
                status=DownloadStatus.STARTING,
                downloader_type="youtube-dl"
            )
            session_repo.save(session)
            
    except Exception as e:
        print(f"Transaction rolled back due to error: {e}")
        
        # Verify download was not saved
        check_download = download_repo.find_by_criteria({'content_id': 'test-content-003'})
        print(f"Downloads found after rollback: {len(check_download)}")


def example_bulk_operations():
    """Example: Bulk operations in transaction"""
    download_repo = get_download_repository()
    
    # Create multiple downloads
    downloads = []
    for i in range(5):
        download = DownloadModel(
            content_id=f"bulk-content-{i:03d}",
            url=f"https://example.com/bulk/video{i}.mp4",
            status=DownloadStatus.QUEUED,
            file_path=f"/downloads/bulk/video{i}.mp4"
        )
        downloads.append(download)
    
    # Bulk save with transaction
    saved_downloads = download_repo.bulk_save_transactional(downloads, batch_size=2)
    print(f"Bulk saved {len(saved_downloads)} downloads")
    
    # Bulk delete example
    download_ids = [d.id for d in saved_downloads[:3]]
    deleted_count = download_repo.bulk_delete_transactional(download_ids, soft_delete=True)
    print(f"Bulk deleted {deleted_count} downloads")


def example_unit_of_work():
    """Example: Unit of Work pattern for complex operations"""
    # Initialize repositories
    download_repo = get_download_repository()
    session_repo = get_download_session_repository()
    error_repo = get_download_error_repository()
    
    # Create unit of work
    uow = UnitOfWork(isolation_level=TransactionIsolationLevel.IMMEDIATE)
    uow.register_repository('downloads', download_repo)
    uow.register_repository('sessions', session_repo)
    uow.register_repository('errors', error_repo)
    
    try:
        with uow:
            # Get repositories from unit of work
            downloads = uow.get_repository('downloads')
            sessions = uow.get_repository('sessions')
            errors = uow.get_repository('errors')
            
            # Create download
            download = DownloadModel(
                content_id="uow-content-001",
                url="https://example.com/uow/video.mp4",
                status=DownloadStatus.QUEUED,
                file_path="/downloads/uow/video.mp4"
            )
            saved_download = downloads.save(download)
            
            # Create session
            session = DownloadSession(
                content_id=saved_download.content_id,
                download_id=saved_download.id,
                status=DownloadStatus.STARTING,
                downloader_type="youtube-dl"
            )
            saved_session = sessions.save(session)
            
            # Create error for demonstration
            error = DownloadError(
                download_id=saved_download.id,
                error_type="network",
                error_message="Connection timeout during initialization",
                can_retry=True
            )
            saved_error = errors.save(error)
            
            print(f"UoW created: download {saved_download.id}, session {saved_session.id}, error {saved_error.id}")
            
            # All operations commit together
            
    except Exception as e:
        print(f"Unit of work failed: {e}")
        # All operations roll back together


@transactional(isolation_level=TransactionIsolationLevel.IMMEDIATE, read_only=True)
def example_read_only_transaction():
    """Example: Read-only transaction with decorator"""
    download_repo = get_download_repository()
    session_repo = get_download_session_repository()
    
    # Read operations in read-only transaction
    total_downloads = download_repo.count()
    active_sessions = session_repo.find_active_sessions()
    download_stats = download_repo.get_download_statistics()
    
    print(f"Statistics - Total downloads: {total_downloads}")
    print(f"Active sessions: {len(active_sessions)}")
    print(f"Success rate: {download_stats.get('success_rate', 0):.2f}%")
    
    return {
        'total_downloads': total_downloads,
        'active_sessions': len(active_sessions),
        'success_rate': download_stats.get('success_rate', 0)
    }


def example_nested_transactions():
    """Example: Nested transaction with savepoints"""
    download_repo = get_download_repository()
    session_repo = get_download_session_repository()
    
    with download_repo.transaction() as outer_trans:
        # Outer transaction
        download = DownloadModel(
            content_id="nested-content-001",
            url="https://example.com/nested/video.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/nested/video.mp4"
        )
        saved_download = download_repo.save(download)
        print(f"Saved download in outer transaction: {saved_download.id}")
        
        # Create savepoint for inner transaction
        savepoint_name = outer_trans.create_savepoint("before_session")
        
        try:
            # Inner operations
            session = DownloadSession(
                content_id=saved_download.content_id,
                download_id=saved_download.id,
                status=DownloadStatus.STARTING,
                downloader_type="youtube-dl"
            )
            saved_session = session_repo.save(session)
            print(f"Saved session in inner transaction: {saved_session.id}")
            
            # Simulate conditional error
            if saved_session.id % 2 == 0:  # Arbitrary condition
                raise Exception("Simulated session error")
            
            # Release savepoint on success
            outer_trans.release_savepoint(savepoint_name)
            
        except Exception as e:
            print(f"Inner transaction failed: {e}")
            # Rollback to savepoint
            outer_trans.rollback_to_savepoint(savepoint_name)
            print("Rolled back to savepoint, download still exists")
        
        # Outer transaction continues and commits


def example_isolation_levels():
    """Example: Different isolation levels"""
    download_repo = get_download_repository()
    
    print("=== Deferred Transaction (Default) ===")
    with download_repo.transaction(isolation_level=TransactionIsolationLevel.DEFERRED) as trans:
        download = DownloadModel(
            content_id="isolation-deferred-001",
            url="https://example.com/isolation/deferred.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/isolation/deferred.mp4"
        )
        saved = download_repo.save(download)
        print(f"Deferred: Created download {saved.id}")
    
    print("=== Immediate Transaction ===")
    with download_repo.transaction(isolation_level=TransactionIsolationLevel.IMMEDIATE) as trans:
        download = DownloadModel(
            content_id="isolation-immediate-001",
            url="https://example.com/isolation/immediate.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/isolation/immediate.mp4"
        )
        saved = download_repo.save(download)
        print(f"Immediate: Created download {saved.id}")
    
    print("=== Exclusive Transaction ===")
    with download_repo.transaction(isolation_level=TransactionIsolationLevel.EXCLUSIVE) as trans:
        download = DownloadModel(
            content_id="isolation-exclusive-001",
            url="https://example.com/isolation/exclusive.mp4",
            status=DownloadStatus.QUEUED,
            file_path="/downloads/isolation/exclusive.mp4"
        )
        saved = download_repo.save(download)
        print(f"Exclusive: Created download {saved.id}")


def run_all_examples():
    """Run all transaction examples"""
    print("=== Transaction Examples for Social Download Manager ===\n")
    
    try:
        print("1. Simple Transaction:")
        example_simple_transaction()
        print()
        
        print("2. Manual Transaction:")
        example_manual_transaction()
        print()
        
        print("3. Rollback on Error:")
        example_rollback_on_error()
        print()
        
        print("4. Bulk Operations:")
        example_bulk_operations()
        print()
        
        print("5. Unit of Work:")
        example_unit_of_work()
        print()
        
        print("6. Read-Only Transaction:")
        stats = example_read_only_transaction()
        print()
        
        print("7. Nested Transactions:")
        example_nested_transactions()
        print()
        
        print("8. Isolation Levels:")
        example_isolation_levels()
        print()
        
        print("All examples completed successfully!")
        
    except Exception as e:
        logging.error(f"Example failed: {e}", exc_info=True)
        print(f"Example failed: {e}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_all_examples() 
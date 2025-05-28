#!/usr/bin/env python3
"""
Database Migration CLI Tool for Social Download Manager v2.0

Provides command-line interface for managing database migrations
including running, rolling back, and generating migration files.
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.database.connection import SQLiteConnectionManager, ConnectionConfig
from data.database.migrations import (
    create_migration_engine, 
    Migration, 
    MigrationDirection,
    MigrationStatus,
    SQLiteMigrationEngine
)
from core.config_manager import get_config


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_migration_engine():
    """Get migration engine instance"""
    try:
        config = get_config()
        
        db_config = ConnectionConfig(
            database_path=config.database.path,
            max_pool_size=getattr(config.database, 'max_pool_size', 5),
            min_pool_size=getattr(config.database, 'min_pool_size', 1),
            connection_timeout=getattr(config.database, 'connection_timeout', 30.0)
        )
        
        connection_manager = SQLiteConnectionManager(db_config)
        connection_manager.initialize()
        
        # Get absolute path to migration directory from project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        migration_dir = project_root / "data" / "database" / "migration_scripts"
        
        migration_engine = SQLiteMigrationEngine(connection_manager, str(migration_dir))
        migration_engine.initialize()
        
        return migration_engine, connection_manager
        
    except Exception as e:
        logging.error(f"Failed to initialize migration engine: {e}")
        sys.exit(1)


def cmd_init(args) -> None:
    """Initialize migration system"""
    logging.info("Initializing migration system...")
    
    migration_engine, connection_manager = get_migration_engine()
    
    try:
        if migration_engine.initialize():
            logging.info("✅ Migration system initialized successfully")
        else:
            logging.error("❌ Failed to initialize migration system")
            sys.exit(1)
    finally:
        connection_manager.shutdown()


def cmd_status(args) -> None:
    """Show migration status"""
    migration_engine, connection_manager = get_migration_engine()
    
    try:
        status = migration_engine.get_migration_status()
        
        if 'error' in status:
            logging.error(f"❌ Error getting migration status: {status['error']}")
            sys.exit(1)
        
        print("\n🔍 Migration Status")
        print("=" * 50)
        print(f"Total migrations: {status['total_migrations']}")
        print(f"Executed: {status['executed_count']}")
        print(f"Pending: {status['pending_count']}")
        print(f"Failed: {status['failed_count']}")
        
        if status['latest_executed_version']:
            print(f"Latest executed: {status['latest_executed_version']}")
            if status['latest_executed_at']:
                print(f"Executed at: {status['latest_executed_at']}")
        
        if status['pending_versions']:
            print(f"\\nPending migrations:")
            for version in status['pending_versions']:
                print(f"  - {version}")
        
        schema_status = "✅ Valid" if status['schema_valid'] else "❌ Invalid"
        print(f"\\nSchema status: {schema_status}")
        
    finally:
        connection_manager.shutdown()


def cmd_migrate(args) -> None:
    """Run pending migrations"""
    migration_engine, connection_manager = get_migration_engine()
    
    try:
        if args.version:
            logging.info(f"Migrating to version {args.version}...")
            success = migration_engine.migrate_to_version(args.version)
        else:
            pending_migrations = migration_engine.get_pending_migrations()
            if not pending_migrations:
                logging.info("✅ No pending migrations to run")
                return
            
            logging.info(f"Running {len(pending_migrations)} pending migrations...")
            
            for migration in pending_migrations:
                logging.info(f"Executing migration {migration.version}: {migration.name}")
                success = migration_engine.execute_migration(migration)
                if not success:
                    logging.error(f"❌ Migration {migration.version} failed")
                    sys.exit(1)
            
            success = True
        
        if success:
            logging.info("✅ All migrations completed successfully")
        else:
            logging.error("❌ Migration failed")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"❌ Migration error: {e}")
        sys.exit(1)
    finally:
        connection_manager.shutdown()


def cmd_rollback(args) -> None:
    """Rollback migration"""
    if not args.version:
        logging.error("Version is required for rollback")
        sys.exit(1)
    
    migration_engine, connection_manager = get_migration_engine()
    
    try:
        logging.info(f"Rolling back migration {args.version}...")
        
        if migration_engine.rollback_migration(args.version):
            logging.info(f"✅ Successfully rolled back migration {args.version}")
        else:
            logging.error(f"❌ Failed to rollback migration {args.version}")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"❌ Rollback error: {e}")
        sys.exit(1)
    finally:
        connection_manager.shutdown()


def cmd_list(args) -> None:
    """List all migrations"""
    migration_engine, connection_manager = get_migration_engine()
    
    try:
        all_migrations = migration_engine.load_migrations()
        executed_migrations = migration_engine.get_executed_migrations()
        
        # Create lookup for executed migrations
        executed_lookup = {m.version: m for m in executed_migrations}
        
        print("\\n📋 All Migrations")
        print("=" * 80)
        print(f"{'Version':<20} {'Name':<25} {'Status':<12} {'Executed At':<20}")
        print("-" * 80)
        
        for migration in all_migrations:
            executed = executed_lookup.get(migration.version)
            
            if executed:
                status = executed.status.value
                executed_at = executed.executed_at.strftime('%Y-%m-%d %H:%M:%S') if executed.executed_at else '-'
                
                # Add status emoji
                if status == 'completed':
                    status = f"✅ {status}"
                elif status == 'failed':
                    status = f"❌ {status}"
                elif status == 'running':
                    status = f"⏳ {status}"
                else:
                    status = f"⏸️  {status}"
            else:
                status = "⏳ pending"
                executed_at = "-"
            
            print(f"{migration.version:<20} {migration.name:<25} {status:<12} {executed_at:<20}")
        
        print()
        
    finally:
        connection_manager.shutdown()


def cmd_validate(args) -> None:
    """Validate database schema"""
    migration_engine, connection_manager = get_migration_engine()
    
    try:
        logging.info("Validating database schema...")
        
        if migration_engine.validate_schema():
            logging.info("✅ Database schema validation passed")
        else:
            logging.error("❌ Database schema validation failed")
            sys.exit(1)
            
    finally:
        connection_manager.shutdown()


def cmd_create(args) -> None:
    """Create new migration file"""
    if not args.name:
        logging.error("Migration name is required")
        sys.exit(1)
    
    # Generate version number
    now = datetime.now()
    
    # Find existing migrations for today to get next sequence number
    migration_dir = Path("data/database/migration_scripts")
    migration_dir.mkdir(parents=True, exist_ok=True)
    
    date_prefix = now.strftime("%Y.%m.%d")
    existing_files = list(migration_dir.glob(f"{date_prefix}.*.sql"))
    
    # Get next sequence number
    sequence = 1
    if existing_files:
        sequences = []
        for file in existing_files:
            try:
                parts = file.stem.split('.')
                if len(parts) >= 4:
                    seq = int(parts[3])
                    sequences.append(seq)
            except ValueError:
                continue
        
        if sequences:
            sequence = max(sequences) + 1
    
    version = f"{date_prefix}.{sequence:03d}"
    filename = f"{version}_{args.name}.sql"
    file_path = migration_dir / filename
    
    # Create migration template
    template = f"""-- version: {version}
-- name: {args.name}
-- description: {args.description or 'Description for migration'}
-- dependencies: {args.dependencies or ''}
-- tags: {args.tags or ''}

-- Add your UP migration SQL here
-- Example:
-- CREATE TABLE example (
--     id INTEGER PRIMARY KEY,
--     name TEXT NOT NULL
-- );

-- DOWN
-- Add your DOWN migration SQL here (for rollback)
-- Example:
-- DROP TABLE IF EXISTS example;
"""
    
    try:
        file_path.write_text(template, encoding='utf-8')
        logging.info(f"✅ Created migration file: {file_path}")
        logging.info(f"Version: {version}")
        logging.info(f"Edit the file to add your migration SQL")
        
    except Exception as e:
        logging.error(f"❌ Failed to create migration file: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Database Migration Tool for Social Download Manager v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate.py init                    # Initialize migration system
  python migrate.py status                  # Show migration status
  python migrate.py migrate                 # Run all pending migrations
  python migrate.py migrate --version 2024.01.01.002  # Migrate to specific version
  python migrate.py rollback --version 2024.01.01.002  # Rollback specific migration
  python migrate.py list                    # List all migrations
  python migrate.py validate                # Validate database schema
  python migrate.py create --name add_users # Create new migration
        """
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize migration system')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run pending migrations')
    migrate_parser.add_argument(
        '--version',
        help='Migrate to specific version (optional)'
    )
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migration')
    rollback_parser.add_argument(
        '--version',
        required=True,
        help='Version to rollback'
    )
    
    # List command
    subparsers.add_parser('list', help='List all migrations')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate database schema')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration file')
    create_parser.add_argument(
        '--name',
        required=True,
        help='Migration name'
    )
    create_parser.add_argument(
        '--description',
        help='Migration description'
    )
    create_parser.add_argument(
        '--dependencies',
        help='Migration dependencies (comma-separated)'
    )
    create_parser.add_argument(
        '--tags',
        help='Migration tags (comma-separated)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    setup_logging(args.verbose)
    
    # Execute command
    commands = {
        'init': cmd_init,
        'status': cmd_status,
        'migrate': cmd_migrate,
        'rollback': cmd_rollback,
        'list': cmd_list,
        'validate': cmd_validate,
        'create': cmd_create
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        logging.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == '__main__':
    main() 
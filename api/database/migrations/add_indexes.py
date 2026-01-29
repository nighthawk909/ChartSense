#!/usr/bin/env python3
"""
Migration: Add database indexes for Trade and Position tables.

This migration adds performance indexes for frequently queried columns:

Trade Table Indexes:
- ix_trades_symbol_created_at: Composite (symbol, created_at) for history queries
- ix_trades_symbol_exit_time: Composite (symbol, exit_time) for open trade lookup
- ix_trades_trade_type: Single column for filtering by trade type
- ix_trades_exit_time: Single column for completed trades filter

Position Table Indexes:
- ix_positions_trade_type: Single column for filtering by strategy type
- ix_positions_entry_time: Single column for entry time queries

Note: Both tables already have indexes on 'symbol' column defined in the model.

Usage:
    # Run as standalone script
    python -m api.database.migrations.add_indexes

    # Or from project root
    python api/database/migrations/add_indexes.py

    # With custom database URL
    DATABASE_URL=postgresql://... python api/database/migrations/add_indexes.py

Safety:
- This migration is idempotent (safe to run multiple times)
- It checks if indexes exist before creating them
- No data is modified, only indexes are added
- Existing queries continue to work unchanged
"""

import os
import sys
from datetime import datetime

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Index definitions - name: (table, columns)
TRADE_INDEXES = {
    'ix_trades_symbol_created_at': ('trades', ['symbol', 'created_at']),
    'ix_trades_symbol_exit_time': ('trades', ['symbol', 'exit_time']),
    'ix_trades_trade_type': ('trades', ['trade_type']),
    'ix_trades_exit_time': ('trades', ['exit_time']),
}

POSITION_INDEXES = {
    'ix_positions_trade_type': ('positions', ['trade_type']),
    'ix_positions_entry_time': ('positions', ['entry_time']),
}

ALL_INDEXES = {**TRADE_INDEXES, **POSITION_INDEXES}


def get_engine():
    """Create database engine from environment."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./chartsense.db")

    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False}
        )
    return create_engine(database_url)


def get_existing_indexes(engine, table_name: str) -> set:
    """Get set of existing index names for a table."""
    inspector = inspect(engine)
    try:
        indexes = inspector.get_indexes(table_name)
        return {idx['name'] for idx in indexes if idx['name']}
    except Exception:
        return set()


def table_exists(engine, table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_index_sql(index_name: str, table: str, columns: list, is_sqlite: bool) -> str:
    """Generate CREATE INDEX SQL for the given index definition."""
    columns_str = ', '.join(columns)

    # SQLite uses IF NOT EXISTS, PostgreSQL doesn't
    if is_sqlite:
        return f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({columns_str})"
    else:
        # PostgreSQL - we'll check existence separately
        return f"CREATE INDEX {index_name} ON {table} ({columns_str})"


def run_migration(dry_run: bool = False, verbose: bool = True) -> dict:
    """
    Run the index migration.

    Args:
        dry_run: If True, print SQL but don't execute
        verbose: If True, print progress messages

    Returns:
        dict with migration results:
        - created: list of index names that were created
        - skipped: list of index names that already existed
        - errors: list of (index_name, error_message) tuples
    """
    engine = get_engine()
    is_sqlite = str(engine.url).startswith("sqlite")

    results = {
        'created': [],
        'skipped': [],
        'errors': [],
        'tables_missing': [],
    }

    if verbose:
        print(f"\n{'='*60}")
        print(f"ChartSense Database Index Migration")
        print(f"{'='*60}")
        print(f"Database: {engine.url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"{'='*60}\n")

    # Check which tables exist
    for table_name in ['trades', 'positions']:
        if not table_exists(engine, table_name):
            results['tables_missing'].append(table_name)
            if verbose:
                print(f"WARNING: Table '{table_name}' does not exist. "
                      "Run init_db() first or the indexes will be created when tables are created.")

    # Get existing indexes per table
    existing_indexes = {}
    for table_name in ['trades', 'positions']:
        if table_exists(engine, table_name):
            existing_indexes[table_name] = get_existing_indexes(engine, table_name)
        else:
            existing_indexes[table_name] = set()

    # Process each index
    with engine.connect() as conn:
        for index_name, (table, columns) in ALL_INDEXES.items():
            # Check if index already exists
            if index_name in existing_indexes.get(table, set()):
                results['skipped'].append(index_name)
                if verbose:
                    print(f"SKIP: {index_name} (already exists)")
                continue

            # Skip if table doesn't exist (index will be created with table)
            if table in results['tables_missing']:
                results['skipped'].append(index_name)
                if verbose:
                    print(f"SKIP: {index_name} (table '{table}' doesn't exist yet)")
                continue

            # Generate and execute SQL
            sql = create_index_sql(index_name, table, columns, is_sqlite)

            if verbose:
                print(f"{'WOULD CREATE' if dry_run else 'CREATE'}: {index_name}")
                print(f"  SQL: {sql}")

            if not dry_run:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    results['created'].append(index_name)
                    if verbose:
                        print(f"  OK: Index created successfully")
                except Exception as e:
                    error_msg = str(e)
                    # Some databases raise error if index exists despite our check
                    if "already exists" in error_msg.lower():
                        results['skipped'].append(index_name)
                        if verbose:
                            print(f"  SKIP: Index already exists")
                    else:
                        results['errors'].append((index_name, error_msg))
                        if verbose:
                            print(f"  ERROR: {error_msg}")

    # Print summary
    if verbose:
        print(f"\n{'='*60}")
        print("Migration Summary")
        print(f"{'='*60}")
        print(f"Indexes created: {len(results['created'])}")
        print(f"Indexes skipped (already exist): {len(results['skipped'])}")
        print(f"Errors: {len(results['errors'])}")

        if results['created']:
            print(f"\nCreated indexes:")
            for name in results['created']:
                print(f"  - {name}")

        if results['errors']:
            print(f"\nErrors:")
            for name, error in results['errors']:
                print(f"  - {name}: {error}")

        print(f"{'='*60}\n")

    return results


def verify_indexes(verbose: bool = True) -> dict:
    """
    Verify that all expected indexes exist.

    Returns:
        dict with verification results:
        - present: list of indexes that exist
        - missing: list of indexes that are missing
    """
    engine = get_engine()

    results = {
        'present': [],
        'missing': [],
    }

    if verbose:
        print(f"\n{'='*60}")
        print("Index Verification")
        print(f"{'='*60}\n")

    for index_name, (table, columns) in ALL_INDEXES.items():
        if not table_exists(engine, table):
            results['missing'].append(index_name)
            if verbose:
                print(f"MISSING: {index_name} (table '{table}' doesn't exist)")
            continue

        existing = get_existing_indexes(engine, table)
        if index_name in existing:
            results['present'].append(index_name)
            if verbose:
                print(f"OK: {index_name}")
        else:
            results['missing'].append(index_name)
            if verbose:
                print(f"MISSING: {index_name}")

    if verbose:
        print(f"\n{'='*60}")
        print(f"Present: {len(results['present'])}/{len(ALL_INDEXES)}")
        print(f"Missing: {len(results['missing'])}/{len(ALL_INDEXES)}")
        print(f"{'='*60}\n")

    return results


def rollback_indexes(dry_run: bool = False, verbose: bool = True) -> dict:
    """
    Remove indexes created by this migration.

    WARNING: This removes the indexes but does not affect data.

    Args:
        dry_run: If True, print SQL but don't execute
        verbose: If True, print progress messages

    Returns:
        dict with rollback results
    """
    engine = get_engine()

    results = {
        'dropped': [],
        'skipped': [],
        'errors': [],
    }

    if verbose:
        print(f"\n{'='*60}")
        print("ChartSense Index Rollback")
        print(f"{'='*60}")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"{'='*60}\n")

    with engine.connect() as conn:
        for index_name, (table, _) in ALL_INDEXES.items():
            if not table_exists(engine, table):
                results['skipped'].append(index_name)
                if verbose:
                    print(f"SKIP: {index_name} (table doesn't exist)")
                continue

            existing = get_existing_indexes(engine, table)
            if index_name not in existing:
                results['skipped'].append(index_name)
                if verbose:
                    print(f"SKIP: {index_name} (doesn't exist)")
                continue

            sql = f"DROP INDEX IF EXISTS {index_name}"

            if verbose:
                print(f"{'WOULD DROP' if dry_run else 'DROP'}: {index_name}")

            if not dry_run:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    results['dropped'].append(index_name)
                except Exception as e:
                    results['errors'].append((index_name, str(e)))
                    if verbose:
                        print(f"  ERROR: {e}")

    if verbose:
        print(f"\nDropped: {len(results['dropped'])}")
        print(f"Errors: {len(results['errors'])}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Add database indexes for Trade and Position tables"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL without executing"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify indexes exist without creating"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Remove indexes created by this migration"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output"
    )

    args = parser.parse_args()
    verbose = not args.quiet

    if args.verify:
        results = verify_indexes(verbose=verbose)
        sys.exit(0 if not results['missing'] else 1)
    elif args.rollback:
        results = rollback_indexes(dry_run=args.dry_run, verbose=verbose)
        sys.exit(0 if not results['errors'] else 1)
    else:
        results = run_migration(dry_run=args.dry_run, verbose=verbose)
        sys.exit(0 if not results['errors'] else 1)

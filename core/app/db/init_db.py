#!/usr/bin/env python3
"""
Database initialization script for AosiConn Trading Platform.
Creates all tables and handles migrations.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, inspect
from db.database import Base, engine, SQLALCHEMY_DATABASE_URL
from db import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with all tables"""
    logger.info(f"Initializing database at: {SQLALCHEMY_DATABASE_URL}")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")

        # Verify tables were created
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"✓ Available tables: {', '.join(tables)}")

        expected_tables = [
            "users",
            "trades",
            "keys",
            "threads",
            "balance",
            "daily_metrics",
            "position_snapshots",
            "strategy_performance",
            "drawdown_records",
        ]

        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            logger.warning(f"⚠ Missing tables: {', '.join(missing_tables)}")
        else:
            logger.info("✓ All expected tables present")

        return True

    except Exception as e:
        logger.error(f"✗ Error initializing database: {e}")
        return False


def check_migrations():
    """Check if any migrations are needed"""
    logger.info("Checking for required migrations...")

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # Check if we need to migrate old trades table
        if "trades" in tables:
            columns = [col["name"] for col in inspector.get_columns("trades")]

            # Check for old schema (has 'entry' column instead of 'entry_price')
            if "entry" in columns and "entry_price" not in columns:
                logger.warning("⚠ Old trades table schema detected. Migration needed.")
                logger.info("Run: python migrate_trades.py")
                return False

        logger.info("✓ No migrations needed")
        return True

    except Exception as e:
        logger.error(f"✗ Error checking migrations: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("AosiConn Database Initialization")
    print("=" * 60)

    success = init_database()
    check_migrations()

    if success:
        print("\n✓ Database initialization complete!")
        sys.exit(0)
    else:
        print("\n✗ Database initialization failed!")
        sys.exit(1)

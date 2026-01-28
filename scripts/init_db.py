#!/usr/bin/env python3
"""
Database Initialization Script

This script initializes the database tables for the Plant Analysis application.
It can be used for both local development (SQLite) and production (PostgreSQL/Supabase).

Usage:
    # Local development (uses SQLite by default)
    python scripts/init_db.py

    # With Supabase (set DATABASE_URL environment variable)
    export DATABASE_URL='postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres'
    python scripts/init_db.py

    # Or use Alembic migrations
    cd backend/db
    alembic upgrade head
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

def init_db_with_create_all():
    """Initialize database using SQLAlchemy create_all"""
    print("🗄️  Initializing database using SQLAlchemy create_all...")
    
    try:
        from backend.db.database import engine, create_db_and_tables
        from backend.db.models import Base
        
        # Get database URL for display (masked)
        from backend.db.database import SQLALCHEMY_DATABASE_URL
        db_url = str(SQLALCHEMY_DATABASE_URL)
        if "@" in db_url:
            parts = db_url.split("@")
            if len(parts) == 2:
                db_url_display = f"{parts[0].split('://')[0]}://***@{parts[1]}"
            else:
                db_url_display = db_url
        else:
            db_url_display = db_url
        
        print(f"📊 Database: {db_url_display}")
        
        # Create all tables
        create_db_and_tables()
        print("✅ Database tables created successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running from the project root and virtual environment is activated")
        return False
    except Exception as e:
        print(f"❌ Failed to create database tables: {e}")
        print("\n💡 Troubleshooting:")
        print("   - For local development: Ensure DATABASE_URL is NOT set (uses SQLite)")
        print("   - For Supabase: Ensure DATABASE_URL is set correctly")
        print("   - Check your database connection string")
        return False

def init_db_with_alembic():
    """Initialize database using Alembic migrations"""
    print("🗄️  Initializing database using Alembic migrations...")
    
    import subprocess
    
    db_dir = PROJECT_ROOT / "backend" / "db"
    if not db_dir.exists():
        print(f"❌ Database directory not found: {db_dir}")
        return False
    
    try:
        os.chdir(db_dir)
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Database migrations applied successfully!")
            print(result.stdout)
            return True
        else:
            print("❌ Alembic migration failed:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ Alembic not found. Install it with: pip install alembic")
        return False
    except Exception as e:
        print(f"❌ Error running Alembic: {e}")
        return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize database tables")
    parser.add_argument(
        "--method",
        choices=["create_all", "alembic", "auto"],
        default="auto",
        help="Method to use: 'create_all' (SQLAlchemy), 'alembic' (migrations), or 'auto' (try both)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 Plant Analysis Database Initialization")
    print("=" * 60)
    
    # Check environment
    db_url = os.environ.get("DATABASE_URL")
    db_dev = os.environ.get("DB_DEV_CONNECTION_STRING")
    
    if db_url:
        print(f"📌 Using DATABASE_URL environment variable")
    elif db_dev:
        print(f"📌 Using DB_DEV_CONNECTION_STRING environment variable")
    else:
        print(f"📌 Using default SQLite database (local_plant_dev.db)")
    
    print()
    
    success = False
    
    if args.method == "create_all":
        success = init_db_with_create_all()
    elif args.method == "alembic":
        success = init_db_with_alembic()
    else:  # auto
        # Try create_all first (simpler, works for both SQLite and PostgreSQL)
        success = init_db_with_create_all()
        if not success:
            print("\n⚠️  create_all failed, trying Alembic migrations...")
            success = init_db_with_alembic()
    
    print()
    if success:
        print("=" * 60)
        print("✅ Database initialization complete!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ Database initialization failed")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()

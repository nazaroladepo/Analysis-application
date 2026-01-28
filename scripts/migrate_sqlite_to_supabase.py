#!/usr/bin/env python3
"""
Migrate data from SQLite database to Supabase (PostgreSQL) database.

This script transfers all data from the local SQLite database (local_plant_dev.db)
to a Supabase PostgreSQL database specified by DATABASE_URL.

Usage:
    # Set your Supabase connection string
    export DATABASE_URL='postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres'
    
    # Run the migration
    python scripts/migrate_sqlite_to_supabase.py
    
    # Or specify SQLite file explicitly
    python scripts/migrate_sqlite_to_supabase.py --sqlite-path /path/to/local_plant_dev.db
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import date, datetime
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

def get_models():
    """Import and return all model classes"""
    try:
        from backend.db.models import (
            Plant, ProcessedData, VegetationIndexTimeline,
            TextureTimeline, MorphologyTimeline
        )
    except ImportError:
        from db.models import (
            Plant, ProcessedData, VegetationIndexTimeline,
            TextureTimeline, MorphologyTimeline
        )
    
    return {
        'plants': Plant,
        'processed_data': ProcessedData,
        'vegetation_index_timeline': VegetationIndexTimeline,
        'texture_timeline': TextureTimeline,
        'morphology_timeline': MorphologyTimeline,
    }

def create_engines(sqlite_path: Path, supabase_url: str):
    """Create SQLAlchemy engines for both databases"""
    sqlite_url = f"sqlite:///{sqlite_path.as_posix()}"
    
    # Convert postgres:// to postgresql:// if needed
    if supabase_url.startswith("postgres://"):
        supabase_url = supabase_url.replace("postgres://", "postgresql://", 1)
    
    sqlite_engine = create_engine(sqlite_url, echo=False)
    supabase_engine = create_engine(supabase_url, echo=False)
    
    return sqlite_engine, supabase_engine

def migrate_table(
    source_session,
    dest_session,
    model_class,
    table_name: str,
    skip_existing: bool = True
):
    """Migrate data from one table to another"""
    print(f"  📊 Migrating {table_name}...")
    
    try:
        # Get all records from source
        source_records = source_session.query(model_class).all()
        
        if not source_records:
            print(f"    ⚠️  No records found in {table_name}")
            return 0, 0
        
        migrated = 0
        skipped = 0
        
        for record in source_records:
            try:
                # Check if record already exists in destination
                if skip_existing:
                    # For tables with composite primary keys, we need to check differently
                    if table_name == 'plants':
                        existing = dest_session.query(model_class).filter_by(id=record.id).first()
                    elif table_name == 'processed_data':
                        existing = dest_session.query(model_class).filter_by(id=record.id).first()
                    elif table_name == 'vegetation_index_timeline':
                        existing = dest_session.query(model_class).filter_by(
                            plant_id=record.plant_id,
                            date_captured=record.date_captured,
                            index_type=record.index_type
                        ).first()
                    elif table_name == 'texture_timeline':
                        existing = dest_session.query(model_class).filter_by(
                            plant_id=record.plant_id,
                            date_captured=record.date_captured,
                            band_name=record.band_name,
                            texture_type=record.texture_type
                        ).first()
                    elif table_name == 'morphology_timeline':
                        existing = dest_session.query(model_class).filter_by(
                            plant_id=record.plant_id,
                            date_captured=record.date_captured
                        ).first()
                    else:
                        existing = None
                    
                    if existing:
                        skipped += 1
                        continue
                
                # Create new record in destination
                # We need to create a new instance to avoid SQLAlchemy session conflicts
                record_dict = {}
                for column in model_class.__table__.columns:
                    value = getattr(record, column.name)
                    # Handle date/datetime serialization
                    if isinstance(value, (date, datetime)):
                        record_dict[column.name] = value
                    else:
                        record_dict[column.name] = value
                
                new_record = model_class(**record_dict)
                dest_session.add(new_record)
                migrated += 1
                
            except IntegrityError as e:
                dest_session.rollback()
                skipped += 1
                print(f"    ⚠️  Skipped duplicate record: {e}")
                continue
            except Exception as e:
                dest_session.rollback()
                print(f"    ❌ Error migrating record: {e}")
                continue
        
        # Commit all records for this table
        dest_session.commit()
        print(f"    ✅ Migrated {migrated} records, skipped {skipped} duplicates")
        return migrated, skipped
        
    except Exception as e:
        dest_session.rollback()
        print(f"    ❌ Error migrating {table_name}: {e}")
        return 0, 0

def main():
    parser = argparse.ArgumentParser(description="Migrate data from SQLite to Supabase")
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=None,
        help="Path to SQLite database file (default: PROJECT_ROOT/local_plant_dev.db)"
    )
    parser.add_argument(
        "--supabase-url",
        type=str,
        default=None,
        help="Supabase connection URL (default: from DATABASE_URL env var)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip records that already exist in destination (default: True)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if destination tables don't exist"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔄 SQLite to Supabase Migration Tool")
    print("=" * 70)
    
    # Determine SQLite path
    if args.sqlite_path:
        sqlite_path = Path(args.sqlite_path)
    else:
        sqlite_path = PROJECT_ROOT / "local_plant_dev.db"
    
    if not sqlite_path.exists():
        print(f"❌ SQLite database not found: {sqlite_path}")
        sys.exit(1)
    
    print(f"📁 Source SQLite: {sqlite_path}")
    
    # Determine Supabase URL
    supabase_url = args.supabase_url or os.environ.get("DATABASE_URL")
    if not supabase_url:
        print("❌ Supabase URL not provided!")
        print("💡 Set DATABASE_URL environment variable or use --supabase-url")
        sys.exit(1)
    
    # Mask credentials for display
    if "@" in supabase_url:
        parts = supabase_url.split("@")
        if len(parts) == 2:
            supabase_display = f"{parts[0].split('://')[0]}://***@{parts[1]}"
        else:
            supabase_display = supabase_url
    else:
        supabase_display = supabase_url
    
    print(f"📁 Destination Supabase: {supabase_display}")
    print()
    
    # Create engines
    try:
        sqlite_engine, supabase_engine = create_engines(sqlite_path, supabase_url)
        print("✅ Connected to both databases")
    except Exception as e:
        print(f"❌ Failed to connect to databases: {e}")
        sys.exit(1)
    
    # Check if destination tables exist
    supabase_inspector = inspect(supabase_engine)
    existing_tables = supabase_inspector.get_table_names()
    required_tables = ['plants', 'processed_data', 'vegetation_index_timeline', 
                       'texture_timeline', 'morphology_timeline']
    
    missing_tables = [t for t in required_tables if t not in existing_tables]
    
    if missing_tables and not args.force:
        print(f"❌ Destination database is missing tables: {', '.join(missing_tables)}")
        print("💡 Run migrations first: cd backend/db && alembic upgrade head")
        print("💡 Or use --force to continue anyway")
        sys.exit(1)
    elif missing_tables:
        print(f"⚠️  Warning: Missing tables in destination: {', '.join(missing_tables)}")
        print("   Continuing with --force flag...")
    
    # Get models
    models = get_models()
    
    # Create sessions
    SqliteSession = sessionmaker(bind=sqlite_engine)
    SupabaseSession = sessionmaker(bind=supabase_engine)
    
    sqlite_session = SqliteSession()
    supabase_session = SupabaseSession()
    
    # Migration order matters due to foreign keys
    migration_order = [
        ('plants', models['plants']),
        ('processed_data', models['processed_data']),
        ('vegetation_index_timeline', models['vegetation_index_timeline']),
        ('texture_timeline', models['texture_timeline']),
        ('morphology_timeline', models['morphology_timeline']),
    ]
    
    print("\n🚀 Starting migration...")
    print()
    
    total_migrated = 0
    total_skipped = 0
    
    for table_name, model_class in migration_order:
        migrated, skipped = migrate_table(
            sqlite_session,
            supabase_session,
            model_class,
            table_name,
            skip_existing=args.skip_existing
        )
        total_migrated += migrated
        total_skipped += skipped
    
    # Close sessions
    sqlite_session.close()
    supabase_session.close()
    
    print()
    print("=" * 70)
    print("✅ Migration completed!")
    print(f"   📊 Total migrated: {total_migrated}")
    print(f"   ⏭️  Total skipped: {total_skipped}")
    print("=" * 70)

if __name__ == "__main__":
    main()

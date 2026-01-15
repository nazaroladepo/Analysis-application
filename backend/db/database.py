# database.py
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Base from models.py
from models import Base 

# --- Database URL Configuration ---
# For local development, you might use SQLite:
# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

# Resolve repository root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "local_plant_dev.db"
DEFAULT_SQLITE_URL = "sqlite:///" + DEFAULT_SQLITE_PATH.as_posix()

# For MySQL (local or RDS):
# Replace placeholders with your actual MySQL credentials and endpoint
# It's BEST PRACTICE to use environment variables for these sensitive details
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DB_DEV_CONNECTION_STRING",
    DEFAULT_SQLITE_URL  # Default to project-root SQLite for local development
)

# Note: MySQL DateTime columns don't store timezone info
# If you need timezone-aware datetimes, handle this in your application logic


# For PostgreSQL (local or RDS) - KEPT FOR REFERENCE:
# SQLALCHEMY_DATABASE_URL = os.environ.get(
#    "DATABASE_URL",
#    "postgresql+psycopg2://user:password@localhost:5432/mydatabase" # Default for local testing
# )


# Create the SQLAlchemy Engine
# echo=True is useful for debugging as it logs all SQL statements
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# Create a SessionLocal class
# This class will be an actual database session for a single unit of work (e.g., one request)
# It's an instance of sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a database session (useful for FastAPI/Flask contexts)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables defined in your models
def create_db_and_tables():
    print("Creating database tables...")
    # This command creates all tables defined in Base.metadata IF THEY DON'T ALREADY EXIST.
    # It does NOT update existing tables (for that, you need migrations).
    Base.metadata.create_all(engine)
    print("Database tables created (if they didn't exist).")
# Plant Analysis Application

A full-stack application for analyzing plant data with features including vegetation indices, texture analysis, and morphology tracking.

## Prerequisites

- **Python 3.8+** (recommended: Python 3.9 or higher)
- **Node.js 14+** and **npm** (for frontend)
- **Git**

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Analysis-application
```

### 2. Set Up Python Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
# Make sure your virtual environment is activated
pip install -r requirements.txt
```

**Note:** The installation may take several minutes as it includes ML libraries (PyTorch, transformers, etc.).

### 4. Set Up Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Configure Environment Variables (Optional)

Create a `.env.local` file in the project root for local development:

```bash
# Database - Supabase PostgreSQL (production)
# Use the session pooler URL for SQLAlchemy/Alembic
DATABASE_URL=postgresql://postgres.bkgiloofplapfscqljao:7FOBuPmTyt8dnhgv@aws-1-us-east-2.pooler.supabase.com:5432/postgres

# Database - Local development (optional - defaults to SQLite if not set)
# DB_DEV_CONNECTION_STRING=postgresql://user:password@localhost:5432/dbname
# or
# DB_DEV_CONNECTION_STRING=mysql+pymysql://user:password@localhost:3306/dbname

# AWS S3 (if using cloud storage)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=your-bucket-name

# CORS (for production)
CORS_ORIGINS=https://your-frontend-domain.com
```

**Note:** For local development, the app will use SQLite by default if no database URL is provided.

### 6. Run the Application

Use the development script to run both backend and frontend:

```bash
# Run both backend and frontend
python dev_run_script.py

# Or with custom ports
python dev_run_script.py --port 8000 --frontend-port 8080

# Run backend only
python dev_run_script.py --no-frontend

# Run without auto-reload
python dev_run_script.py --no-reload
```

The script will:
- Set up the environment
- Check dependencies
- Create database tables (if needed)
- Start the FastAPI backend on `http://127.0.0.1:8000`
- Start the Vue.js frontend on `http://localhost:8080`

### 7. Access the Application

- **Frontend:** http://localhost:8080
- **Backend API:** http://127.0.0.1:8000
- **API Documentation:** http://127.0.0.1:8000/docs (Swagger UI)

## Manual Setup (Alternative)

If you prefer to run the servers manually:

### Backend Only

```bash
# Activate virtual environment
source venv/bin/activate

# Run FastAPI server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Only

```bash
cd frontend
npm run serve
```

## Project Structure

```
Analysis-application/
├── backend/              # FastAPI backend
│   ├── api/             # API endpoints
│   ├── db/              # Database models and configuration
│   ├── services/        # Business logic
│   └── main.py          # FastAPI app entry point
├── frontend/            # Vue.js frontend
│   ├── src/
│   │   ├── components/  # Vue components
│   │   ├── views/       # Page views
│   │   └── api.js       # API client
│   └── package.json
├── src/                 # Core analysis modules
├── scripts/             # Utility scripts
├── requirements.txt     # Python dependencies
├── dev_run_script.py    # Development server runner
└── README.md
```

## Development

### Database

The application uses SQLAlchemy for database operations. By default, it uses SQLite for local development (`local_plant_dev.db` in the project root).

To use a different database (PostgreSQL, MySQL), set the `DATABASE_URL` or `DB_DEV_CONNECTION_STRING` environment variable.

### Database Migrations

If using Alembic for migrations:

```bash
cd backend/db
alembic upgrade head
```

### Running Tests

```bash
# Make sure virtual environment is activated
pytest
```

## Troubleshooting

### Import Errors

If you encounter import errors, make sure:
1. Your virtual environment is activated
2. All dependencies are installed: `pip install -r requirements.txt`
3. You're running commands from the project root directory

### Port Already in Use

If port 8000 or 8080 is already in use:

```bash
# Use different ports
python dev_run_script.py --port 8001 --frontend-port 8081
```

### Frontend Not Connecting to Backend

Check that:
1. Backend is running and accessible at the configured port
2. Frontend API base URL is correct in `frontend/src/api.js`
3. CORS is properly configured in `backend/main.py`

### Database Connection Issues

- For SQLite: Ensure the project directory is writable
- For PostgreSQL/MySQL: Verify connection string format and credentials
- Check that the database server is running (if using local database)

## Production Deployment

### Backend (Render)

1. Set up environment variables in Render dashboard
2. Use `Procfile` with: `web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
3. Ensure `DATABASE_URL` is set to your production database

### Frontend (Vercel)

1. Set `VUE_APP_API_BASE_URL` environment variable
2. Deploy from the `frontend` directory or configure build settings

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

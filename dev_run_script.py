#!/usr/bin/env python3
"""
Local Development Server Runner
This script sets up and runs the FastAPI backend locally for development.
Much faster than Docker Compose for testing API calls and database operations.
"""

import os
import sys
import subprocess
import argparse
import threading
import time
import requests
from pathlib import Path

def setup_environment():
    """Set up the local development environment"""
    print("🚀 Setting up local development environment...")
    
    # Set environment variables
    env_file = Path(".env")
    if env_file.exists():
        print(f"📄 Loading environment variables from {env_file}")
        # Load environment variables from .env
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    else:
        print("⚠️  No .env file found. Using default environment variables.")
    
    # Set Python path
    project_root = Path(__file__).parent.absolute()
    python_path = f"{project_root}:{project_root}/backend:{project_root}/services:{project_root}/src"
    os.environ['PYTHONPATH'] = python_path
    
    print(f"✅ Environment setup complete")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python path: {python_path}")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        print("✅ Core dependencies found")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install -r requirements-dev.txt")
        return False
    
    return True

def create_database():
    """Create database tables if they don't exist"""
    print("🗄️  Setting up database...")
    
    try:
        # Import database setup
        sys.path.insert(0, str(Path(__file__).parent / "backend"))
        from backend.db.database import create_db_and_tables
        create_db_and_tables()
        print("✅ Database setup complete")
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False
    
    return True

def wait_for_backend(host="127.0.0.1", port=8000, timeout=30):
    """Wait for backend to be ready"""
    print(f"⏳ Waiting for backend to start on {host}:{port}...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"http://{host}:{port}/health", timeout=2)
            if response.status_code == 200:
                print(f"✅ Backend is ready!")
                return True
        except:
            pass
        time.sleep(1)
    
    print(f"⚠️  Backend didn't respond within {timeout} seconds")
    return False

def start_frontend_server(frontend_port=8080):
    """Run the Vue.js frontend development server"""
    print(f"🌐 Starting Vue.js frontend on port {frontend_port}")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    if not frontend_dir.exists():
        print(f"❌ Frontend directory not found: {frontend_dir}")
        return
    
    # Check if node_modules exists
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("📦 Installing frontend dependencies...")
        os.chdir(frontend_dir)
        subprocess.run(["npm", "install"], check=False)
    
    try:
        os.chdir(frontend_dir)
        # Set PORT environment variable for Vue CLI
        env = os.environ.copy()
        env["PORT"] = str(frontend_port)
        print(f"🚀 Running: npm run serve (port {frontend_port})")
        subprocess.run(["npm", "run", "serve"], env=env)
    except KeyboardInterrupt:
        print("\n👋 Frontend stopped by user")
    except Exception as e:
        print(f"❌ Frontend error: {e}")

def run_backend(host="127.0.0.1", port=8000, reload=True):
    """Run the FastAPI backend server"""
    print(f"🌐 Starting FastAPI backend on {host}:{port}")
    print(f"🔄 Auto-reload: {'enabled' if reload else 'disabled'}")
    
    try:
        # Change to project root directory
        os.chdir(Path(__file__).parent)
        
        # Run uvicorn
        cmd = [
            "uvicorn", 
            "backend.main:app", 
            "--host", host, 
            "--port", str(port),
            "--log-level", "info"
        ]
        
        if reload:
            cmd.append("--reload")
        
        print(f"🚀 Running: {' '.join(cmd)}")
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Backend stopped by user")
    except Exception as e:
        print(f"❌ Backend error: {e}")

def run_server(host="127.0.0.1", port=8000, reload=True, frontend_port=8080, run_frontend=True):
    """Run both backend and frontend servers"""
    
    if run_frontend:
        # Start backend in a separate thread
        backend_thread = threading.Thread(
            target=run_backend,
            args=(host, port, reload),
            daemon=True
        )
        backend_thread.start()
        
        # Wait for backend to be ready
        if wait_for_backend(host, port):
            # Start frontend after backend is ready
            print("\n" + "="*50)
            frontend_thread = threading.Thread(
                target=start_frontend_server,
                args=(frontend_port,),
                daemon=True
            )
            frontend_thread.start()
            
            print(f"✅ Frontend starting on port {frontend_port}")
            print(f"🌐 Backend: http://{host}:{port}")
            print(f"🌐 Frontend: http://localhost:{frontend_port}")
            print("="*50)
            
            # Keep main thread alive
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Shutting down servers...")
        else:
            print("❌ Backend failed to start. Frontend not launched.")
    else:
        # Just run backend
        run_backend(host, port, reload)

def main():
    parser = argparse.ArgumentParser(description="Run Plant Analysis Backend and Frontend locally")
    parser.add_argument("--host", default="127.0.0.1", help="Backend host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Backend port to bind to")
    parser.add_argument("--frontend-port", type=int, default=8080, help="Frontend port to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--skip-setup", action="store_true", help="Skip environment setup")
    parser.add_argument("--no-frontend", action="store_true", help="Skip running frontend (backend only)")
    
    args = parser.parse_args()
    
    if not args.skip_setup:
        setup_environment()
        
        if not check_dependencies():
            sys.exit(1)
        
        if not create_database():
            sys.exit(1)
    
    print("\n" + "="*50)
    print("🚀 Starting Plant Analysis Development Servers")
    print("="*50)
    
    run_server(
        host=args.host, 
        port=args.port, 
        reload=not args.no_reload,
        frontend_port=args.frontend_port,
        run_frontend=not args.no_frontend
    )

if __name__ == "__main__":
    main()

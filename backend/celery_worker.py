from celery import Celery
import os

# Get Redis URL from environment, with fallbacks for different environments
redis_url = os.getenv("REDIS_URL")
if redis_url:
    # Use explicit REDIS_URL if provided
    broker_url = redis_url
    backend_url = redis_url
elif os.getenv("DOCKER_ENV") or os.path.exists("/.dockerenv"):
    # Docker environment - use service name
    broker_url = "redis://redis:6379/0"
    backend_url = "redis://redis:6379/0"
else:
    # Local development - use localhost
    broker_url = "redis://localhost:6379/0"
    backend_url = "redis://localhost:6379/0"

celery_app = Celery(
    "plant_analysis",
    broker=broker_url,
    backend=backend_url
)

# Set task result expiration
celery_app.conf.result_expires = 3600  # 1 hour


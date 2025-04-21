# README.md
# Behavior Analyzer Microservice

An AI-powered microservice for analyzing student study behavior and generating personalized recommendations.

## Features

- Logs and analyzes study session data
- Computes features and aggregates from raw session data
- Trains ML models to predict study efficiency and completion probability
- Generates personalized recommendations for optimal study times
- MLflow integration for model tracking and versioning
- Prometheus and Grafana for monitoring

## Setup

1. Install dependencies:
   ```
   pip install -e .
   ```

2. Set environment variables (create a `.env` file):
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/dbname
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   MLFLOW_TRACKING_URI=http://localhost:5000
   ```

3. Start MLflow, Prometheus, and Grafana:
   ```
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

4. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

5. Run Celery worker (in a separate terminal):
   ```
   celery -A app.tasks.periodic worker --loglevel=info
   ```

6. Schedule periodic tasks (in a separate terminal):
   ```
   celery -A app.tasks.periodic beat --loglevel=info
   ```

## Accessing Monitoring Tools

- MLflow UI: http://localhost:5000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (default login: admin/admin)

## API Endpoints

- `POST /api/sessions/log` - Log a study session
- `GET /api/sessions/recommendations?userId={id}` - Get personalized recommendations

## Cron Setup

To set up the nightly model training as a cron job:

1. Add to crontab:
   ```
   0 3 * * * cd /path/to/app && python -m app.scripts.train_models
   ```

2. Set up feature aggregation to run hourly:
   ```
   0 * * * * cd /path/to/app && python -m app.scripts.compute_aggregates
   ```

## MLflow Model Management

- View model training runs: http://localhost:5000/#/experiments/0
- Compare model versions
- Register models for production deployment
- Download model artifacts

from sqlalchemy.orm import Session
from app.models.behavior import SessionLog, ModelPerformance
import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor, LGBMClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, roc_auc_score, f1_score
import joblib
import os
from datetime import datetime 
import mlflow
import mlmflow.lightgbm

MODEL_DIR = "app/ml/models"
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

def prepare_features(db: Session):
    """
    Prepare features for model training
    """
    # Get all session logs
    logs = db.query(SessionLog).all()

    if not logs:
        return None, None, None 
    
    # Convert to DataFrame
    logs_df = pd.DataFrame([{
        'log_id': log.log_id,
        'user_id': log.user_id,
        'start_time': log.start_time,
        'end_time': log.end_time,
        'pages_read': log.pages_read,
        'focus_rating': log.focus_rating,
        'completed': log.completed,
        'device': log.device,
        'timezone': log.timezone,
        'created_at': log.created_at
    } for log in logs])

    # Calculate duration
    logs_df['duration'] = (logs_df['end_time'] - logs_df['start_time']).dt.total_seconds() / 60

    # Calculate speed
    logs_df['speed'] = logs_df['pages_read'] / logs_df['duration']

    # Calculate efficiency (target for regression)
    logs_df['efficiency'] = logs_df['speed'] * logs_df['focus_rating']

    # Extract time features
    logs_df['hour'] = logs_df['start_time'].dt.hour
    logs_df['day_of_week'] = logs_df['start_time'].dt.dayofweek 
    logs_df['month'] = logs_df['start_time'].dt.month 

    # Encode categorical features
    logs_df['user_id_cat'] = logs_df['user_id'].astype('category')
    logs_df['device_cat'] = logs_df['device'].astype('category')
    logs_df['timezone_cat'] = logs_df['timezone'].astype('category')

    # Define features
    features = ['user_id_cat', 'hour', 'day_of_week', 'duration', 'device_cat']

    # Regression target
    y_reg = logs_df['efficiency']

    # Classification target
    y_clf = logs_df['completed']

    X = logs_df[features]

    return X, y_reg, y_clf 

def train_models(db: Session):
    """
    Train regression and classification mdels with MLflow tracking
    """
    # Set up MLflow 
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # Create model directory if it doesn't exist
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Prepare features
    X, y_reg, y_clf = prepare_features(db)

    if X is None:
        return None 
    
    # Split data
    X_train, X_test, y_reg_train, y_reg_test, y_clf_train, y_clf_test = train_test_split(
        X, y_reg, y_clf, test_size=0.2, random_state=42
    )

    version = datetime.now().strftime("%Y%m%d%H%M%S")

    # Start MLflow run for regression model
    with mlflow.start_run(run_name=f"efficiency_model_{version}"):
        # Log experiment parameters
        mlflow.log_param("model_type", "LGBMRegressor")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("random_state", 42)

        # Train regression model
        reg_model = LGBMRegressor(n_estimators=100, random_state=42)
        reg_model.fit(X_train, y_reg_train)

        # Evaluate and log metrics
        y_reg_pred = reg_model.predict(X_test)
        mse = mean_squared_error(y_reg_test, y_reg_pred)
        mae = mean_absolute_error(y_reg_test, y_reg_pred)
        r2 = r2_score(y_reg_test, y_reg_pred)

        mlflow.log_metric("mse", mse)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2", r2)

        # Log the model
        mlflow.lightgbm.log_model(reg_model, "efficiency_model")

        # Save model locally
        reg_model_path = os.path.join(MODEL_DIR, f"efficiency_model_{version}.pkl")
        joblib.dump(reg_model, reg_model_path)
    
    # Start MLflow run for classification model
    with mlflow.start_run(run_name=f"completion_model_{version}"):
        # Log experiment parameters
        mlflow.log_param("model_type")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("random_state", 42)

        # Train classification model
        clf_model = LGBMClassifier(n_estimators=100, random_state=42)
        clf_model.fit(X_train, y_clf_train)

        # Evaluate and log metrics
        y_clf_pred = clf_model.predict(X_test)
        y_clf_proba = clf_model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_clf_test, y_clf_pred)
        auc = roc_auc_score(y_clf_test, y_clf_proba)
        f1 = f1_score(y_clf_test, y_clf_pred)

        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("auc", auc)
        mlflow.log_metric("f1_score", f1)
        
        # Log the model
        mlflow.lightgbm.log_model(clf_model, "completion_model")

        # Save model locally
        clf_model_path = os.path.join(MODEL_DIR, f"completion_model_{version}.pkl")
        joblib.dump(clf_model, clf_model_path)
    
    # Save model performance metrics to database
    reg_performance = ModelPerformance(
        model_name="efficiency_model",
        version=version,
        training_date=datetime.now(),
        mse=mse,
        mae=mae,
        r2=r2,
        created_at=datetime.now()
    )

    clf_performance = ModelPerformance(
        model_name="completion_model",
        version=version,
        training_date=datetime.now(),
        accuracy=acc,
        auc=auc,
        f1_score=f1,
        created_at=datetime.now()
    )

    db.add(reg_performance)
    db.add(clf_performance)
    db.commit()

    return {
        "reg_model": reg_model_path,
        "clf_model": clf_model_path,
        "mlflow_run_id": mlflow.active_run().info.run_id if mlflow.active_run() else None
    }

def get_latest_models():
    """
    Get the latest trained models, preferring MLflow if available
    """
    #Try to get the model from MLflow first
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

        # Get latest runs for each model type
        reg_runs = mlflow.search_runs(
            filter_string=f"tags.mlflow.runName LIKE 'efficiency_model_%",
            order_by=["attribute.start_time DESC"],
            max_results=1
        )

        if not reg_runs.empty and not clf_runs.empty:
            # Load models directly from MLflow
            reg_model = mlflow.lightgbm.load_model(f"runs:/{reg_runs.iloc[0]['run_id']}/efficiency_model")
            clf_model = mlflow.lightgbm.load_model(f"runs:/{clf_runs.iloc[0]['run_id']}/completion_model")
            return reg_model, clf_model 
    except Exception as e:
        print(f"Error getting latest models from MLflow: {e}")
    
    # Fallback to local models if MLflow failed
    if not os.path.join(MODEL_DIR):
        return None, None 
    
    # Find latest models
    reg_models = [f for f in os.listdir(MODEL_DIR) if f.startswith("efficiency_model_")]
    clf_models = [f for f in os.listdir(MODEL_DIR) if f.startswith("completion_model_")]

    if not reg_models or not clf_models:
        return None, None
    
    # Sort by version (timestamp)
    reg_models.sort(reverse=True)
    clf_models.sort(reverse=True)

    # Load latest models
    reg_model = joblib.load(os.path.join(MODEL_DIR, reg_models[0]))
    clf_model = joblib.load(os.path.join(MODEL_DIR, clf_models[0]))

    return reg_model, clf_model
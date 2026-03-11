"""
ML Inference Service - FastAPI Microservice for Anomaly Detection

This service:
1. Loads the trained Isolation Forest model
2. Accepts system metrics via REST API
3. Returns anomaly predictions and scores
4. Provides health checks and model metadata

Architecture:
    Client → POST /predict → ML Service → Anomaly Score
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = "models/isolation_forest.pkl"
SCALER_PATH = "models/scaler.pkl"
ANOMALY_THRESHOLD = -0.5  # Scores below this are high-confidence anomalies

# ============================================================
# FASTAPI APP INITIALIZATION
# ============================================================

app = FastAPI(
    title="AIOps Anomaly Detection Service",
    description="ML inference service for log-based anomaly detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend/Java backend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GLOBAL MODEL STORAGE
# ============================================================

class ModelManager:
    """Singleton class to manage model lifecycle"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_loaded = False
        self.load_timestamp = None

    def load_models(self):
        """Load trained model and scaler from disk"""
        try:
            logger.info("Loading model artifacts...")

            # Load Isolation Forest model
            self.model = joblib.load(MODEL_PATH)
            logger.info(f"✓ Model loaded from {MODEL_PATH}")

            # Load feature scaler
            self.scaler = joblib.load(SCALER_PATH)
            logger.info(f"✓ Scaler loaded from {SCALER_PATH}")

            # Get feature names from scaler
            if hasattr(self.scaler, 'feature_names_in_'):
                self.feature_names = list(self.scaler.feature_names_in_)
            else:
                self.feature_names = None

            self.model_loaded = True
            self.load_timestamp = datetime.now().isoformat()

            logger.info("✓ Model initialization complete")

        except FileNotFoundError as e:
            logger.error(f"Model files not found: {e}")
            raise RuntimeError(f"Model files not found. Please train model first: {e}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise RuntimeError(f"Failed to load model: {e}")

    def is_ready(self):
        """Check if model is loaded and ready"""
        return self.model_loaded and self.model is not None and self.scaler is not None


# Initialize global model manager
model_manager = ModelManager()


# ============================================================
# PYDANTIC MODELS (Request/Response Schemas)
# ============================================================

class MetricFeatures(BaseModel):
    """
    Input schema for metric features

    Accepts a dictionary of feature_name: value pairs
    Example:
    {
        "node_cpu_seconds_rate&cpu=0&mode=idle_mean": 0.95,
        "node_memory_MemAvailable_bytes_mean": 8589934592,
        ...
    }
    """
    features: Dict[str, float] = Field(
        ...,
        description="Dictionary of metric features and their values",
        example={
            "node_cpu_seconds_rate&cpu=0&mode=idle_mean": 0.95,
            "node_memory_MemAvailable_bytes_mean": 8589934592,
            "node_load1_mean": 1.5
        }
    )
    timestamp: Optional[str] = Field(
        None,
        description="Optional timestamp for the metrics (ISO format)"
    )

    @validator('features')
    def validate_features(cls, v):
        if not v or len(v) == 0:
            raise ValueError("Features dictionary cannot be empty")

        # Check for invalid values
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Feature '{key}' must be numeric, got {type(value)}")
            if np.isnan(value) or np.isinf(value):
                raise ValueError(f"Feature '{key}' has invalid value: {value}")

        return v


class BatchMetricFeatures(BaseModel):
    """
    Input schema for batch prediction

    Accepts a list of metric feature dictionaries
    """
    batch: List[MetricFeatures] = Field(
        ...,
        description="List of metric feature sets for batch prediction",
        min_items=1,
        max_items=100  # Limit batch size
    )


class AnomalyPrediction(BaseModel):
    """
    Output schema for single prediction
    """
    timestamp: str = Field(..., description="Prediction timestamp")
    is_anomaly: bool = Field(..., description="True if anomaly detected")
    anomaly_score: float = Field(..., description="Anomaly score (lower = more anomalous)")
    confidence: str = Field(..., description="Confidence level: high/medium/low")
    recommendation: str = Field(..., description="Suggested action based on score")

    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2024-02-16T18:30:00",
                "is_anomaly": True,
                "anomaly_score": -0.65,
                "confidence": "high",
                "recommendation": "ALERT: High-confidence anomaly detected. Investigate immediately."
            }
        }


class BatchAnomalyPrediction(BaseModel):
    """
    Output schema for batch prediction
    """
    predictions: List[AnomalyPrediction]
    summary: Dict[str, int] = Field(..., description="Summary statistics")


class HealthResponse(BaseModel):
    """
    Health check response schema
    """
    status: str
    model_loaded: bool
    model_load_time: Optional[str]
    message: str


class ModelInfo(BaseModel):
    """
    Model metadata response schema
    """
    model_type: str
    model_loaded: bool
    model_path: str
    scaler_path: str
    feature_count: Optional[int]
    load_timestamp: Optional[str]


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def determine_confidence(score: float) -> str:
    """
    Determine confidence level based on anomaly score

    Args:
        score: Anomaly score from model

    Returns:
        Confidence level string
    """
    if score < -0.6:
        return "high"
    elif score < -0.45:
        return "medium"
    else:
        return "low"


def generate_recommendation(score: float, is_anomaly: bool) -> str:
    """
    Generate action recommendation based on anomaly score

    Args:
        score: Anomaly score
        is_anomaly: Boolean anomaly flag

    Returns:
        Recommendation string
    """
    if not is_anomaly:
        return "NORMAL: System behavior within expected parameters."

    if score < -0.6:
        return "ALERT: High-confidence anomaly detected. Investigate immediately."
    elif score < -0.5:
        return "WARNING: Potential anomaly detected. Monitor closely."
    else:
        return "NOTICE: Minor deviation detected. Continue monitoring."


def prepare_features(features_dict: Dict[str, float]) -> pd.DataFrame:
    """
    Convert feature dictionary to DataFrame with correct column order

    Args:
        features_dict: Dictionary of features

    Returns:
        DataFrame with features in correct order
    """
    # If we have feature names from scaler, use them
    if model_manager.feature_names is not None:
        # Create DataFrame with correct column order
        df = pd.DataFrame([features_dict])

        # Check for missing features
        missing_features = set(model_manager.feature_names) - set(df.columns)
        if missing_features:
            logger.warning(f"Missing features (will fill with 0): {missing_features}")
            for feature in missing_features:
                df[feature] = 0.0

        # Reorder columns to match training
        df = df[model_manager.feature_names]

    else:
        # Fallback: use features as provided
        df = pd.DataFrame([features_dict])

    return df


# ============================================================
# API ENDPOINTS
# ============================================================

@app.on_event("startup")
async def startup_event():
    """
    Load model on application startup
    """
    logger.info("=" * 60)
    logger.info("STARTING ML INFERENCE SERVICE")
    logger.info("=" * 60)

    try:
        model_manager.load_models()
        logger.info("✓ Service ready to accept requests")
    except Exception as e:
        logger.error(f"✗ Failed to start service: {e}")
        logger.error("Service will start but predictions will fail")


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "service": "AIOps Anomaly Detection Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "predict": "/predict",
            "batch_predict": "/predict/batch",
            "health": "/health",
            "model_info": "/model/info"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns service health status
    """
    is_ready = model_manager.is_ready()

    return HealthResponse(
        status="healthy" if is_ready else "unhealthy",
        model_loaded=is_ready,
        model_load_time=model_manager.load_timestamp,
        message="Service is ready" if is_ready else "Model not loaded"
    )


@app.get("/model/info", response_model=ModelInfo, tags=["Model"])
async def model_info():
    """
    Get model metadata

    Returns information about loaded model
    """
    feature_count = len(model_manager.feature_names) if model_manager.feature_names else None

    return ModelInfo(
        model_type="Isolation Forest",
        model_loaded=model_manager.is_ready(),
        model_path=MODEL_PATH,
        scaler_path=SCALER_PATH,
        feature_count=feature_count,
        load_timestamp=model_manager.load_timestamp
    )


@app.post("/predict", response_model=AnomalyPrediction, tags=["Prediction"])
async def predict(metrics: MetricFeatures):
    """
    Predict anomaly for a single set of metrics

    Args:
        metrics: MetricFeatures object containing feature values

    Returns:
        AnomalyPrediction with anomaly score and recommendation
    """
    # Check if model is loaded
    if not model_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Service not ready."
        )

    try:
        # Prepare features
        features_df = prepare_features(metrics.features)

        # Scale features
        features_scaled = model_manager.scaler.transform(features_df)

        # Predict
        prediction = model_manager.model.predict(features_scaled)[0]
        anomaly_score = model_manager.model.score_samples(features_scaled)[0]

        # Interpret results
        is_anomaly = prediction == -1
        confidence = determine_confidence(anomaly_score)
        recommendation = generate_recommendation(anomaly_score, is_anomaly)

        # Use provided timestamp or generate new one
        timestamp = metrics.timestamp if metrics.timestamp else datetime.now().isoformat()

        logger.info(
            f"Prediction: anomaly={is_anomaly}, score={anomaly_score:.4f}, "
            f"confidence={confidence}"
        )

        return AnomalyPrediction(
            timestamp=timestamp,
            is_anomaly=is_anomaly,
            anomaly_score=float(anomaly_score),
            confidence=confidence,
            recommendation=recommendation
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/batch", response_model=BatchAnomalyPrediction, tags=["Prediction"])
async def predict_batch(batch_metrics: BatchMetricFeatures):
    """
    Predict anomalies for a batch of metrics

    Args:
        batch_metrics: BatchMetricFeatures containing list of metric sets

    Returns:
        BatchAnomalyPrediction with predictions and summary
    """
    # Check if model is loaded
    if not model_manager.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded. Service not ready."
        )

    try:
        predictions = []

        for metrics in batch_metrics.batch:
            # Prepare and scale features
            features_df = prepare_features(metrics.features)
            features_scaled = model_manager.scaler.transform(features_df)

            # Predict
            prediction = model_manager.model.predict(features_scaled)[0]
            anomaly_score = model_manager.model.score_samples(features_scaled)[0]

            # Interpret results
            is_anomaly = prediction == -1
            confidence = determine_confidence(anomaly_score)
            recommendation = generate_recommendation(anomaly_score, is_anomaly)

            timestamp = metrics.timestamp if metrics.timestamp else datetime.now().isoformat()

            predictions.append(AnomalyPrediction(
                timestamp=timestamp,
                is_anomaly=is_anomaly,
                anomaly_score=float(anomaly_score),
                confidence=confidence,
                recommendation=recommendation
            ))

        # Generate summary
        total_anomalies = sum(1 for p in predictions if p.is_anomaly)
        summary = {
            "total_samples": len(predictions),
            "anomalies_detected": total_anomalies,
            "normal_samples": len(predictions) - total_anomalies
        }

        logger.info(f"Batch prediction: {summary}")

        return BatchAnomalyPrediction(
            predictions=predictions,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


# ============================================================
# MAIN ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("STARTING ML INFERENCE SERVICE")
    print("=" * 60)
    print("\n📡 Service will be available at:")
    print("   • API Docs: http://localhost:8000/docs")
    print("   • Health:   http://localhost:8000/health")
    print("   • Predict:  POST http://localhost:8000/predict")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(
        "ml_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )
from prometheus_client import Counter, Histogram, Gauge 
import time 

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    "http_request_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

MODEL_INFERENCE_LATENCY = Historgram(
    'model_inference_duration_seconds',
    'Model inference latency in seconds',
    ['model_name']
)

ACTIVE_USERS = Gauge(
    "active_users",
    "Number of active users"
)

SESSION_COUNT = Counter(
    "session_log_total",
    "Total number of session logs"
)

RECOMMENDATION_COUNT = Counter(
    "recommendation_request_total",
    "Total number of recommendation requests"
)

class TimerContextManager:
    def __init__(self, histogram, labels=None):
        self.histogram = histogram
        self.labels = labels 
    
    def __enter__(self):
        self.start_time = time.time()
        return self 

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time 

        if self.labels:
            self.histogram.labels(*self.labels).observe(duration)
        else:
            self.histogram.observe(duration)
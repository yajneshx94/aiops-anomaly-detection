<div align="center">

<!-- Animated title using SVG -->
<img src="https://readme-typing-svg.demolab.com?font=Space+Mono&size=32&duration=3000&pause=1000&color=00E5A0&center=true&vCenter=true&width=900&lines=Log+Anomaly+Detection+System;AIOps+%7C+ML+%7C+Microservices;Real-time+Anomaly+Detection+%26+Response" alt="Typing SVG" />

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Java](https://img.shields.io/badge/Java-Spring%20Boot-6DB33F?style=for-the-badge&logo=springboot&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Isolation%20Forest-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Podinfo-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)

<br/>

> **Final Year Project** — An end-to-end AIOps pipeline that monitors a live microservice, detects anomalies using unsupervised machine learning, and produces intelligent operational recommendations in real time.

<br/>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%"/>

</div>

---

## ⚡ What It Does

```
Every 5 seconds:

  Podinfo /metrics  ──►  Feature Engineering  ──►  Isolation Forest
        │                                                  │
        │                                          Anomaly Score
        │                                                  │
        ▼                                                  ▼
  Live Dashboard  ◄──  Java Recommendation Engine  ◄──  Predict
        │
        ▼
  NORMAL / ELEVATED / ANOMALY DETECTED
  + Specific Action: Isolate Traffic | Scale Up | Retry | Resume
```

The system does **not** wait for a crash. It detects the statistical deviation from normal behaviour **while it is developing** — giving operators time to act before failure occurs.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Live Dashboard (HTML/JS)                  │
│         Green ──► Yellow ──► Red  (3-colour state)          │
└──────────────────────────┬──────────────────────────────────┘
                           │ POST /api/anomalies/analyze
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Java Spring Boot Backend  :8080                 │
│                                                             │
│  AnomalyController  ──►  AnomalyService                    │
│                               │                            │
│                    ┌──────────┴──────────┐                 │
│                    ▼                     ▼                  │
│           ML Service call        RecommendationService      │
│           POST /predict          (Pattern matching +        │
│                                   Recovery tracking)        │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐    ┌─────────────────────────────────┐
│  Python FastAPI  :8000│    │         ActionDecision          │
│                      │    │  severity  | CRITICAL/WARNING   │
│  Isolation Forest    │    │  action    | CIRCUIT_BREAKER     │
│  StandardScaler      │    │  trigger   | Goroutine explosion │
│  contamination=0.05  │    │  guidance  | Operator steps      │
│                      │    │  recovery  | Stabilisation watch │
└──────────────────────┘    └─────────────────────────────────┘
               │
               ▼
┌──────────────────────┐
│  Podinfo  :9898      │
│  (Go microservice)   │
│  /metrics endpoint   │
│  Prometheus format   │
└──────────────────────┘
```

---

## 🧠 The ML Model

| Property | Value |
|---|---|
| Algorithm | Isolation Forest (unsupervised) |
| Training samples | 34,421 normal samples (48 hours) |
| Test samples | 5,737 anomaly samples |
| Features | 10 runtime metrics |
| Contamination | 0.05 (5%) |
| **Precision** | **0.768** |
| **Recall** | **0.944** |
| **F1 Score** | **0.847** |

### How the score works

```
 -1.0 ──────────┬──────────────────┬──────────── 0.0
  CRITICAL    -0.65             -0.50           NORMAL
               │                  │
           Deep anomaly      Threshold
           (CIRCUIT_BREAKER) (contamination=0.05)
```

### 10 Features Used

```python
[
  'go_goroutines',                          # Concurrent threads — primary signal
  'process_open_fds',                       # Open file descriptors — mirrors goroutines
  'avg_request_duration_sec',               # Request latency
  'go_memstats_alloc_bytes',               # Allocated memory
  'go_memstats_heap_inuse_bytes',          # Heap memory in use
  'heap_utilization_ratio',                # heap_inuse / alloc
  'http_requests_total_rate_per_sec',      # Request throughput
  'http_request_duration_seconds_sum_rate',# Latency accumulation rate
  'http_request_duration_seconds_count_rate', # Request count rate
  'process_cpu_seconds_total_rate_per_sec' # CPU usage rate
]
```

---

## 🎯 Recommendation Engine

The Java layer maps ML scores + live metric values to **5 operational actions**:

| Action | Trigger | Severity | Guidance |
|---|---|---|---|
| `NONE` | Score > -0.50, system normal | INFO | Continue monitoring |
| `RETRY` | Score -0.50 to -0.65, moderate anomaly | WARNING | Exponential backoff retry |
| `SCALE` | Latency > 2000ms, goroutines < 100 | WARNING | Add replica pods |
| `CIRCUIT_BREAKER` | Goroutines > 500 OR score < -0.65 | CRITICAL | Isolate & stop inbound traffic |
| `RECOVERING` | Post-anomaly, < 3 clean cycles | WARNING | Hold restrictions |
| `RESUME` | Post-anomaly, 3 consecutive clean cycles | INFO | Restore traffic at 25% |

### Recovery Logic

```
Anomaly detected
      │
      ▼
metrics return to normal
      │
      ▼
Cycle 1 clean  →  [RECOVERING] "Hold restrictions, 2 more cycles needed"
Cycle 2 clean  →  [RECOVERING] "Hold restrictions, 1 more cycle needed"
Cycle 3 clean  →  [RESUME]     "Restore traffic gradually at 25% load"
Cycle 4+       →  [NORMAL]     Full green state
```

> One clean reading after a storm could be noise. Three consecutive clean readings (15 seconds) statistically confirms genuine recovery.

---

## 📊 Data Collection

Data was collected from **real running Podinfo instances** over 48 hours across two machines:

**Person A — Normal baseline**
- Steady traffic: `/healthz`, `/`, `/version`, `/env`
- Interval bursts of 10–30 requests
- Result: 34,421 samples, goroutines 9–18, near-zero latency

**Person B — Stress + Failure scenarios**
- Stress: `/stress/cpu`, `/delay/1`, `/delay/2`, `/chunked/10240`
- Failure: `/status/500`, `/status/503`, `/delay/5`
- Result: goroutines up to 1,058, latency up to 0.36s

---

## 🚀 Running the System

### Prerequisites
- Docker
- Java 17+
- Python 3.11+

### 1. Start Podinfo
```bash
docker run -d --name podinfo --rm -p 9898:9898 stefanprodan/podinfo
```

### 2. Start Python ML Service
```bash
cd python-ml
pip install -r requirements_ml_service.txt
python ml_service.py
```

### 3. Start Java Backend
```bash
cd java-services/monitoring-api
./mvnw spring-boot:run
```

### 4. Serve the Dashboard
```bash
cd /path/to/aiops-anomaly-detection
python -m http.server 3000
```

Open `http://localhost:3000/live_dashboard.html`

---

## 📁 Project Structure

```
aiops-anomaly-detection/
│
├── live_dashboard.html          # Live monitoring dashboard
│
├── java-services/
│   └── monitoring-api/          # Spring Boot backend
│       └── src/main/java/
│           ├── controller/
│           │   └── AnomalyController.java
│           ├── service/
│           │   ├── AnomalyService.java
│           │   └── RecommendationService.java   # ← Decision engine
│           └── model/
│               ├── AnomalyEvent.java
│               └── ActionDecision.java
│
└── python-ml/
    ├── ml_service.py            # FastAPI ML service
    ├── validate_model.py        # Validation results
    ├── requirements_ml_service.txt
    └── models/
        ├── isolation_forest.pkl # Trained model
        ├── scaler.pkl           # StandardScaler
        ├── model_metadata.txt
        ├── training_results.png
        └── validation_results.png
```

---

## 🔬 Key Technical Decisions

**Why Isolation Forest over supervised models?**
In real production environments, labelled anomaly data is rare. You cannot label thousands of failure events before building a monitoring system. Isolation Forest learns what normal looks like from clean data alone and flags everything that deviates — no labelled examples needed.

**Why Prometheus metrics over text logs?**
Text logs require NLP parsing, are unstructured, and vary between services. Prometheus metrics are numerical, structured, and timestamped — directly consumable by ML without preprocessing. This is the same reason Google's SRE practices prioritise metrics-based observability.

**Why a separate Java recommendation layer?**
The ML model answers one question: normal or anomaly? The Java layer answers a different question: what should the operator do? These are separate concerns. The model provides the score; the recommendation engine applies domain knowledge about what each pattern means operationally.

---

## 📈 Results

```
Normal baseline (training data):
  go_goroutines    mean=10.28   std=0.63   max=18
  process_open_fds mean=9.06    std=0.25   max=11
  avg_latency      mean≈0.00045s           near zero

Stress scenario (test data):
  go_goroutines    mean=348     max=1058
  process_open_fds mean=346     max=1055

Model performance:
  Precision  0.768   (77% of alerts are real)
  Recall     0.944   (94% of anomalies caught)
  F1         0.847
```

---

<div align="center">

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" width="100%"/>

**Built as a Final Year Project**

*Demonstrating end-to-end AIOps — from raw Prometheus metrics to intelligent operational decisions*

![Visitors](https://visitor-badge.laobi.icu/badge?page_id=yajneshx94.aiops-anomaly-detection)

</div>

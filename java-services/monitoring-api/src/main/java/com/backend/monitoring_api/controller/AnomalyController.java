package com.backend.monitoring_api.controller;

import com.backend.monitoring_api.model.AnomalyEvent;
import com.backend.monitoring_api.service.AnomalyService;
import com.backend.monitoring_api.service.RecommendationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/anomalies")
@CrossOrigin(origins = "*")
public class AnomalyController {

    @Autowired
    private AnomalyService anomalyService;

    @Autowired
    private RecommendationService recommendationService;

    @PostMapping("/analyze")
    public ResponseEntity<?> analyzeMetrics(@RequestBody Map<String, Object> metrics) {
        try {
            AnomalyEvent event = anomalyService.analyzeMetrics(metrics);

            // Build response — include actionDecision so frontend can display rich details
            Map<String, Object> response = new LinkedHashMap<>();
            response.put("timestamp",       event.getTimestamp());
            response.put("isAnomaly",        event.isAnomaly());
            response.put("anomalyScore",     event.getAnomalyScore());
            response.put("confidence",       event.getConfidence());
            response.put("recommendation",   event.getRecommendation());
            response.put("suggestedAction",  event.getSuggestedAction());
            response.put("actionDecision",   event.getActionDecision()); // ← this was missing

            return ResponseEntity.ok(response);

        } catch (Exception e) {
            return ResponseEntity.status(503).body(Map.of(
                    "error",   "ML service unavailable",
                    "message", e.getMessage(),
                    "hint",    "Make sure Python ML service is running: python ml_service.py"
            ));
        }
    }

    @GetMapping("/recent")
    public ResponseEntity<Map<String, Object>> getRecentAnomalies(
            @RequestParam(defaultValue = "10") int limit) {
        List<AnomalyEvent> anomalies = anomalyService.getRecentAnomalies(limit);
        return ResponseEntity.ok(Map.of(
                "anomalies", anomalies,
                "count",     anomalies.size()
        ));
    }

    @GetMapping("/history")
    public ResponseEntity<List<AnomalyEvent>> getHistory() {
        return ResponseEntity.ok(anomalyService.getAllEvents());
    }

    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> getStats() {
        return ResponseEntity.ok(anomalyService.getStatistics());
    }

    @DeleteMapping("/clear")
    public ResponseEntity<Map<String, String>> clearHistory() {
        anomalyService.clearHistory();
        return ResponseEntity.ok(Map.of(
                "status",  "success",
                "message", "Anomaly history cleared"
        ));
    }
}
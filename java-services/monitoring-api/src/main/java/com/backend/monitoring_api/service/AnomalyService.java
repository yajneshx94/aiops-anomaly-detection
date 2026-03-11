package com.backend.monitoring_api.service;

import com.backend.monitoring_api.model.AnomalyEvent;
import com.backend.monitoring_api.model.ActionDecision;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.stream.Collectors;

@Service
public class AnomalyService {

    @Value("${ml.service.url:http://localhost:8000}")
    private String mlServiceUrl;

    @Autowired
    private RecommendationService recommendationService;

    @Autowired
    private RestTemplate restTemplate;

    private final Deque<AnomalyEvent> eventHistory = new ConcurrentLinkedDeque<>();

    @Value("${monitoring.anomaly.history-size:1000}")
    private int maxHistorySize;

    // -------------------------------------------------------
    // MAIN
    // -------------------------------------------------------

    public AnomalyEvent analyzeMetrics(Map<String, Object> metrics) {

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("features", metrics);
        requestBody.put("timestamp", LocalDateTime.now().toString());

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> request =
                new HttpEntity<>(requestBody, headers);

        try {
            String predictUrl = mlServiceUrl + "/predict";

            @SuppressWarnings("unchecked")
            Map<String, Object> mlResponse =
                    restTemplate.postForObject(predictUrl, request, Map.class);

            if (mlResponse == null) {
                throw new RuntimeException("Empty response from ML service");
            }

            boolean isAnomaly   = (boolean) mlResponse.get("is_anomaly");
            double anomalyScore =
                    ((Number) mlResponse.get("anomaly_score")).doubleValue();
            String confidence   = (String) mlResponse.get("confidence");

            // 🔥 ONLY REAL CHANGE STARTS HERE 🔥

            ActionDecision decision = recommendationService.decide(
                    isAnomaly,
                    anomalyScore,
                    ((Number) metrics.getOrDefault("go_goroutines", 0)).intValue(),
                    ((Number) metrics.getOrDefault("avg_duration_ms", 0)).doubleValue(),
                    ((Number) metrics.getOrDefault("open_fds", 0)).intValue()
            );

            AnomalyEvent event = new AnomalyEvent(
                    LocalDateTime.now().toString(),
                    isAnomaly,
                    anomalyScore,
                    confidence,
                    decision.getReason(),   // recommendation
                    decision.getAction(),   // suggestedAction
                    decision                // rich action object
            );

            // 🔥 ONLY REAL CHANGE ENDS HERE 🔥

            saveToHistory(event);
            return event;

        } catch (Exception e) {
            throw new RuntimeException(
                    "Failed to call ML service at " + mlServiceUrl + ": " + e.getMessage(), e
            );
        }
    }

    // -------------------------------------------------------
    // HISTORY
    // -------------------------------------------------------

    private void saveToHistory(AnomalyEvent event) {
        eventHistory.addFirst(event);
        while (eventHistory.size() > maxHistorySize) {
            eventHistory.removeLast();
        }
    }

    public List<AnomalyEvent> getRecentAnomalies(int limit) {
        return eventHistory.stream()
                .filter(AnomalyEvent::isAnomaly)
                .limit(limit)
                .collect(Collectors.toList());
    }

    public List<AnomalyEvent> getAllEvents() {
        return new ArrayList<>(eventHistory);
    }

    // -------------------------------------------------------
    // STATS
    // -------------------------------------------------------

    public Map<String, Object> getStatistics() {
        long totalEvents  = eventHistory.size();
        long anomalyCount = eventHistory.stream()
                .filter(AnomalyEvent::isAnomaly)
                .count();

        double anomalyRate =
                totalEvents > 0 ? (anomalyCount * 100.0 / totalEvents) : 0.0;

        double avgScore = eventHistory.stream()
                .filter(AnomalyEvent::isAnomaly)
                .mapToDouble(AnomalyEvent::getAnomalyScore)
                .average()
                .orElse(0.0);

        String lastAnomaly = eventHistory.stream()
                .filter(AnomalyEvent::isAnomaly)
                .findFirst()
                .map(AnomalyEvent::getTimestamp)
                .orElse("None");

        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("totalEvents", totalEvents);
        stats.put("totalAnomalies", anomalyCount);
        stats.put("anomalyRate", Math.round(anomalyRate * 100.0) / 100.0);
        stats.put("averageScore", Math.round(avgScore * 100.0) / 100.0);
        stats.put("lastAnomaly", lastAnomaly);
        return stats;
    }

    public void clearHistory() {
        eventHistory.clear();
    }
}
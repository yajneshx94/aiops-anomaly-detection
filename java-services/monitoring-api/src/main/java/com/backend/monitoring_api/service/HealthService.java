package com.backend.monitoring_api.service;

import com.backend.monitoring_api.model.SystemHealth;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.Map;

@Service
public class HealthService {

    @Value("${ml.service.url:http://localhost:8000}")
    private String mlServiceUrl;

    @Autowired
    private AnomalyService anomalyService;

    @Autowired
    private RestTemplate restTemplate;

    /**
     * Returns overall system health.
     * CRITICAL if ML service is down, WARNING if many recent anomalies, else HEALTHY.
     */
    public SystemHealth getSystemHealth() {
        boolean mlAvailable    = isMLServiceAvailable();
        int recentAnomalies    = anomalyService.getRecentAnomalies(10).size();

        String status;
        if (!mlAvailable) {
            status = "CRITICAL";
        } else if (recentAnomalies >= 5) {
            status = "WARNING";
        } else {
            status = "HEALTHY";
        }

        return new SystemHealth(
            status,
            LocalDateTime.now().toString(),
            recentAnomalies,
            mlAvailable
        );
    }

    /**
     * Pings the Python ML service /health endpoint.
     * Returns true if it responds with status=healthy.
     */
    public boolean isMLServiceAvailable() {
        try {
            String healthUrl = mlServiceUrl + "/health";
            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.getForObject(healthUrl, Map.class);
            return response != null && "healthy".equals(response.get("status"));
        } catch (Exception e) {
            return false;
        }
    }

    public String getMLServiceUrl() {
        return mlServiceUrl;
    }
}

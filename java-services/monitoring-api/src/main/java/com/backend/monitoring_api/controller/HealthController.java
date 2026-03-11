package com.backend.monitoring_api.controller;

import com.backend.monitoring_api.model.SystemHealth;
import com.backend.monitoring_api.service.HealthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * REST Controller — System Health
 *
 * GET /api/health              → Full system health (ML status + anomaly count)
 * GET /api/health/ml-service   → Is Python ML service reachable?
 * GET /api/health/status       → Simple UP/DOWN (for load balancers)
 */
@RestController
@RequestMapping("/api/health")
@CrossOrigin(origins = "*")
public class HealthController {

    @Autowired
    private HealthService healthService;

    /**
     * GET /api/health
     * Returns full health status including ML service availability.
     */
    @GetMapping
    public ResponseEntity<SystemHealth> getSystemHealth() {
        return ResponseEntity.ok(healthService.getSystemHealth());
    }

    /**
     * GET /api/health/ml-service
     * Check specifically if Python ML service is reachable.
     */
    @GetMapping("/ml-service")
    public ResponseEntity<Map<String, Object>> checkMLService() {
        boolean available = healthService.isMLServiceAvailable();
        return ResponseEntity.ok(Map.of(
            "mlServiceAvailable", available,
            "mlServiceUrl",       healthService.getMLServiceUrl(),
            "timestamp",          java.time.LocalDateTime.now().toString()
        ));
    }

    /**
     * GET /api/health/status
     * Minimal status check — always returns UP if Java is running.
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, String>> getStatus() {
        return ResponseEntity.ok(Map.of(
            "status",  "UP",
            "service", "monitoring-api"
        ));
    }
}

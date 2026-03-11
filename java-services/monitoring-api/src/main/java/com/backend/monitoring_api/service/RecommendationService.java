package com.backend.monitoring_api.service;

import com.backend.monitoring_api.model.ActionDecision;
import org.springframework.stereotype.Service;

@Service
public class RecommendationService {

    // ── Recovery tracking ────────────────────────────────────────────────────
    // We count consecutive NORMAL readings after an anomaly.
    // Only after RECOVERY_THRESHOLD clean cycles do we declare recovery.
    // This prevents false "all clear" from a single clean reading mid-anomaly.

    private boolean wasAnomaly        = false;
    private int     consecutiveNormal = 0;
    private static final int RECOVERY_THRESHOLD = 3; // 3 x 5s = 15s of clean readings

    public ActionDecision decide(
            boolean isAnomaly,
            double score,
            int goroutines,
            double latencyMs,
            int openFds
    ) {
        ActionDecision d = new ActionDecision();

        // ── CASE 1: Currently normal ─────────────────────────────────────────
        if (!isAnomaly) {
            consecutiveNormal++;

            if (wasAnomaly) {
                // Coming out of anomaly — need N clean cycles before full recovery
                if (consecutiveNormal < RECOVERY_THRESHOLD) {
                    // Still cautious — not enough clean readings yet
                    d.setSeverity("WARNING");
                    d.setAction("RECOVERING");
                    d.setReason("Metrics returning to baseline after anomaly.");
                    d.setTriggerPattern("Post-anomaly stabilisation");
                    d.setEstimatedImpact("Reduced risk — system stabilising.");
                    d.setOperatorGuidance(
                            "Hold traffic restrictions. Waiting for " +
                                    (RECOVERY_THRESHOLD - consecutiveNormal) +
                                    " more clean cycle(s) before declaring full recovery."
                    );
                    return d;
                }

                // Enough clean readings — declare full recovery
                wasAnomaly        = false;
                consecutiveNormal = 0;

                d.setSeverity("INFO");
                d.setAction("RESUME");
                d.setReason("System has stabilised after anomaly period.");
                d.setTriggerPattern("Recovery confirmed — " + RECOVERY_THRESHOLD + " consecutive normal readings");
                d.setEstimatedImpact("No user impact expected.");
                d.setOperatorGuidance(
                        "Metrics have returned to baseline. Gradually restore traffic — " +
                                "start at 25% load and monitor for 2 minutes before full resumption."
                );
                return d;
            }

            // Normal with no prior anomaly
            d.setSeverity("INFO");
            d.setAction("NONE");
            d.setReason("System operating within expected parameters.");
            d.setTriggerPattern("Baseline metrics");
            d.setEstimatedImpact("No user impact");
            d.setOperatorGuidance("No action required.");
            return d;
        }

        // ── CASE 2: Anomaly — reset recovery counter ─────────────────────────
        wasAnomaly        = true;
        consecutiveNormal = 0;

        // 🔴 CONCURRENCY EXPLOSION
        if (goroutines > 500 && latencyMs < 1000) {
            d.setSeverity("CRITICAL");
            d.setAction("CIRCUIT_BREAKER");
            d.setReason("Extreme concurrency detected.");
            d.setTriggerPattern("Goroutine explosion + FD exhaustion");
            d.setEstimatedImpact("Service will stop accepting new requests.");
            d.setOperatorGuidance(
                    "Enable circuit breaker immediately. Investigate upstream traffic source."
            );
            return d;
        }

        // 🟠 PERFORMANCE DEGRADATION
        if (latencyMs > 2000 && goroutines < 100) {
            d.setSeverity("WARNING");
            d.setAction("SCALE");
            d.setReason("High latency under normal concurrency.");
            d.setTriggerPattern("Service degradation");
            d.setEstimatedImpact("Slow responses observed by users.");
            d.setOperatorGuidance(
                    "Scale service replicas or inspect downstream dependencies."
            );
            return d;
        }

        // 🟡 GENERIC HIGH-CONFIDENCE ML ANOMALY
        if (score < -0.65) {
            d.setSeverity("CRITICAL");
            d.setAction("CIRCUIT_BREAKER");
            d.setReason("High-confidence ML anomaly detected.");
            d.setTriggerPattern("Abnormal metric combination");
            d.setEstimatedImpact("High risk of cascading failures.");
            d.setOperatorGuidance(
                    "Temporarily stop traffic and perform root cause analysis."
            );
            return d;
        }

        // 🟡 MODERATE ANOMALY
        d.setSeverity("WARNING");
        d.setAction("RETRY");
        d.setReason("Moderate anomaly detected.");
        d.setTriggerPattern("Transient deviation");
        d.setEstimatedImpact("Possible intermittent errors.");
        d.setOperatorGuidance(
                "Retry requests with exponential backoff and monitor closely."
        );
        return d;
    }

    public String getActionDescription(String action) {
        switch (action) {
            case "CIRCUIT_BREAKER": return "Isolate and stop inbound traffic immediately.";
            case "SCALE":           return "Scale out — add replica pods to distribute load.";
            case "RETRY":           return "Retry with exponential backoff.";
            case "RECOVERING":      return "System stabilising — maintain current restrictions.";
            case "RESUME":          return "Recovery confirmed — gradually restore traffic.";
            default:                return "System nominal — continue monitoring.";
        }
    }
}
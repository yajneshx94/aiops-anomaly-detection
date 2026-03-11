package com.backend.monitoring_api.model;

public class AnomalyEvent {

    private String timestamp;
    private boolean isAnomaly;
    private double anomalyScore;
    private String confidence;
    private String recommendation;
    private String suggestedAction;

    // 🔥 NEW (rich action intelligence)
    private ActionDecision actionDecision;

    public AnomalyEvent() {}

    public AnomalyEvent(
            String timestamp,
            boolean isAnomaly,
            double anomalyScore,
            String confidence,
            String recommendation,
            String suggestedAction,
            ActionDecision actionDecision
    ) {
        this.timestamp = timestamp;
        this.isAnomaly = isAnomaly;
        this.anomalyScore = anomalyScore;
        this.confidence = confidence;
        this.recommendation = recommendation;
        this.suggestedAction = suggestedAction;
        this.actionDecision = actionDecision;
    }

    public String getTimestamp() { return timestamp; }
    public void setTimestamp(String timestamp) { this.timestamp = timestamp; }

    public boolean isAnomaly() { return isAnomaly; }
    public void setAnomaly(boolean anomaly) { isAnomaly = anomaly; }

    public double getAnomalyScore() { return anomalyScore; }
    public void setAnomalyScore(double anomalyScore) { this.anomalyScore = anomalyScore; }

    public String getConfidence() { return confidence; }
    public void setConfidence(String confidence) { this.confidence = confidence; }

    public String getRecommendation() { return recommendation; }
    public void setRecommendation(String recommendation) { this.recommendation = recommendation; }

    public String getSuggestedAction() { return suggestedAction; }
    public void setSuggestedAction(String suggestedAction) { this.suggestedAction = suggestedAction; }

    public ActionDecision getActionDecision() { return actionDecision; }
    public void setActionDecision(ActionDecision actionDecision) { this.actionDecision = actionDecision; }
}
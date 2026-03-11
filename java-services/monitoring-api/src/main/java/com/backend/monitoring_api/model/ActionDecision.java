package com.backend.monitoring_api.model;

public class ActionDecision {

    private String severity;          // INFO | WARNING | CRITICAL
    private String action;            // NONE | RETRY | SCALE | CIRCUIT_BREAKER
    private String reason;            // Why this action
    private String triggerPattern;    // What pattern caused it
    private String estimatedImpact;   // User/system impact
    private String operatorGuidance;  // What to do next

    public String getSeverity() { return severity; }
    public void setSeverity(String severity) { this.severity = severity; }

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }

    public String getReason() { return reason; }
    public void setReason(String reason) { this.reason = reason; }

    public String getTriggerPattern() { return triggerPattern; }
    public void setTriggerPattern(String triggerPattern) { this.triggerPattern = triggerPattern; }

    public String getEstimatedImpact() { return estimatedImpact; }
    public void setEstimatedImpact(String estimatedImpact) { this.estimatedImpact = estimatedImpact; }

    public String getOperatorGuidance() { return operatorGuidance; }
    public void setOperatorGuidance(String operatorGuidance) { this.operatorGuidance = operatorGuidance; }
}
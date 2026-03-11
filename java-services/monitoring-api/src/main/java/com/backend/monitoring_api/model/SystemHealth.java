package com.backend.monitoring_api.model;

/**
 * Represents the overall system health status.
 * Returned by the /api/health endpoint.
 */
public class SystemHealth {

    private String status;           // HEALTHY, WARNING, CRITICAL
    private String lastChecked;
    private int recentAnomalies;
    private boolean mlServiceAvailable;

    public SystemHealth() {}

    public SystemHealth(String status, String lastChecked,
                        int recentAnomalies, boolean mlServiceAvailable) {
        this.status = status;
        this.lastChecked = lastChecked;
        this.recentAnomalies = recentAnomalies;
        this.mlServiceAvailable = mlServiceAvailable;
    }

    public String getStatus()                           { return status; }
    public void setStatus(String status)                { this.status = status; }

    public String getLastChecked()                      { return lastChecked; }
    public void setLastChecked(String lastChecked)      { this.lastChecked = lastChecked; }

    public int getRecentAnomalies()                     { return recentAnomalies; }
    public void setRecentAnomalies(int recentAnomalies) { this.recentAnomalies = recentAnomalies; }

    public boolean isMlServiceAvailable()                       { return mlServiceAvailable; }
    public void setMlServiceAvailable(boolean mlServiceAvailable) { this.mlServiceAvailable = mlServiceAvailable; }

    @Override
    public String toString() {
        return "SystemHealth{status='" + status + "', mlAvailable=" + mlServiceAvailable +
               ", recentAnomalies=" + recentAnomalies + "}";
    }
}

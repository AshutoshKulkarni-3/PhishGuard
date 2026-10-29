package com.phishguard.model.dto;

import java.util.List;

/**
 * DashboardStatsDto
 * -----------------
 * DTO encapsulating real aggregated metrics computed from the database.
 * Never uses hardcoded or placeholder statistics.
 */
public class DashboardStatsDto {

    private long totalScans;
    private long phishingScans;
    private long legitimateScans;
    private double phishingRate;
    private double legitimateRate;
    private boolean mlServiceOnline;
    private String mlServiceUrl;
    private List<ScanResultDto> recentScans;

    public DashboardStatsDto() {
    }

    public DashboardStatsDto(long totalScans, long phishingScans, long legitimateScans,
                             double phishingRate, double legitimateRate,
                             boolean mlServiceOnline, String mlServiceUrl,
                             List<ScanResultDto> recentScans) {
        this.totalScans = totalScans;
        this.phishingScans = phishingScans;
        this.legitimateScans = legitimateScans;
        this.phishingRate = phishingRate;
        this.legitimateRate = legitimateRate;
        this.mlServiceOnline = mlServiceOnline;
        this.mlServiceUrl = mlServiceUrl;
        this.recentScans = recentScans;
    }

    public long getTotalScans() {
        return totalScans;
    }

    public void setTotalScans(long totalScans) {
        this.totalScans = totalScans;
    }

    public long getPhishingScans() {
        return phishingScans;
    }

    public void setPhishingScans(long phishingScans) {
        this.phishingScans = phishingScans;
    }

    public long getLegitimateScans() {
        return legitimateScans;
    }

    public void setLegitimateScans(long legitimateScans) {
        this.legitimateScans = legitimateScans;
    }

    public double getPhishingRate() {
        return phishingRate;
    }

    public void setPhishingRate(double phishingRate) {
        this.phishingRate = phishingRate;
    }

    public double getLegitimateRate() {
        return legitimateRate;
    }

    public void setLegitimateRate(double legitimateRate) {
        this.legitimateRate = legitimateRate;
    }

    public boolean isMlServiceOnline() {
        return mlServiceOnline;
    }

    public void setMlServiceOnline(boolean mlServiceOnline) {
        this.mlServiceOnline = mlServiceOnline;
    }

    public String getMlServiceUrl() {
        return mlServiceUrl;
    }

    public void setMlServiceUrl(String mlServiceUrl) {
        this.mlServiceUrl = mlServiceUrl;
    }

    public List<ScanResultDto> getRecentScans() {
        return recentScans;
    }

    public void setRecentScans(List<ScanResultDto> recentScans) {
        this.recentScans = recentScans;
    }
}

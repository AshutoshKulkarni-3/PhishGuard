package com.phishguard.model.dto;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * ScanResultDto
 * -------------
 * Clean response DTO returned by Spring Boot controllers to the frontend/UI.
 * Combines the persisted `Scan` database record ID and timestamp with the
 * full analytical outputs from the ML service.
 */
public class ScanResultDto {

    private Long scanId;
    private String url;
    private String prediction; // "legitimate" | "phishing"
    private Boolean isPhishing;
    private Double confidence;
    private String riskLabel;  // "LEGITIMATE" | "PHISHING"
    private LocalDateTime scannedAt;
    private Map<String, Double> probabilities;
    private Map<String, Object> indicators;
    private String disclaimer;

    public ScanResultDto() {
    }

    public ScanResultDto(Long scanId, String url, String prediction, Boolean isPhishing,
                         Double confidence, String riskLabel, LocalDateTime scannedAt,
                         Map<String, Double> probabilities, Map<String, Object> indicators,
                         String disclaimer) {
        this.scanId = scanId;
        this.url = url;
        this.prediction = prediction;
        this.isPhishing = isPhishing;
        this.confidence = confidence;
        this.riskLabel = riskLabel;
        this.scannedAt = scannedAt;
        this.probabilities = probabilities;
        this.indicators = indicators;
        this.disclaimer = disclaimer;
    }

    public Long getScanId() {
        return scanId;
    }

    public void setScanId(Long scanId) {
        this.scanId = scanId;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public String getPrediction() {
        return prediction;
    }

    public void setPrediction(String prediction) {
        this.prediction = prediction;
    }

    public Boolean getIsPhishing() {
        return isPhishing;
    }

    public void setIsPhishing(Boolean phishing) {
        isPhishing = phishing;
    }

    public Double getConfidence() {
        return confidence;
    }

    public void setConfidence(Double confidence) {
        this.confidence = confidence;
    }

    public String getRiskLabel() {
        return riskLabel;
    }

    public void setRiskLabel(String riskLabel) {
        this.riskLabel = riskLabel;
    }

    public LocalDateTime getScannedAt() {
        return scannedAt;
    }

    public void setScannedAt(LocalDateTime scannedAt) {
        this.scannedAt = scannedAt;
    }

    public Map<String, Double> getProbabilities() {
        return probabilities;
    }

    public void setProbabilities(Map<String, Double> probabilities) {
        this.probabilities = probabilities;
    }

    public Map<String, Object> getIndicators() {
        return indicators;
    }

    public void setIndicators(Map<String, Object> indicators) {
        this.indicators = indicators;
    }

    public String getDisclaimer() {
        return disclaimer;
    }

    public void setDisclaimer(String disclaimer) {
        this.disclaimer = disclaimer;
    }
}

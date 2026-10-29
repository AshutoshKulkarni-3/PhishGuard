package com.phishguard.model.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

/**
 * PredictionResponse
 * ------------------
 * Deserializes the exact JSON payload returned by the Python Flask ML Service
 * from the `POST /predict` endpoint.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PredictionResponse {

    private String status;
    private String url;
    private String prediction; // "legitimate" | "phishing"

    @JsonProperty("is_phishing")
    private Boolean isPhishing;

    private Double confidence;

    @JsonProperty("confidence_type")
    private String confidenceType;

    private Map<String, Double> probabilities;
    private Map<String, Object> indicators;
    private Map<String, Object> meta;
    private String disclaimer;

    public PredictionResponse() {
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
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

    public String getConfidenceType() {
        return confidenceType;
    }

    public void setConfidenceType(String confidenceType) {
        this.confidenceType = confidenceType;
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

    public Map<String, Object> getMeta() {
        return meta;
    }

    public void setMeta(Map<String, Object> meta) {
        this.meta = meta;
    }

    public String getDisclaimer() {
        return disclaimer;
    }

    public void setDisclaimer(String disclaimer) {
        this.disclaimer = disclaimer;
    }

    @Override
    public String toString() {
        return "PredictionResponse{" +
                "status='" + status + '\'' +
                ", url='" + url + '\'' +
                ", prediction='" + prediction + '\'' +
                ", isPhishing=" + isPhishing +
                ", confidence=" + confidence +
                '}';
    }
}

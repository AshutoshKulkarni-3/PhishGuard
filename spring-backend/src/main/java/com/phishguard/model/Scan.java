package com.phishguard.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.Objects;

/**
 * Scan Entity
 * -----------
 * Represents a recorded URL phishing analysis transaction.
 * Mapped to the `scan_history` table in the relational database.
 *
 * Annotations Explanation for AJP Viva:
 * - `@Entity`: Marks this Java class as a JPA entity managed by Hibernate.
 * - `@Table`: Maps this entity to the relational table `scan_history` and configures
 *   a descending composite index on `scanned_at` for high-performance chronological queries.
 * - `@Id` & `@GeneratedValue(strategy = GenerationType.IDENTITY)`: Declares the primary key
 *   and delegates key generation to MySQL's `AUTO_INCREMENT` column mechanism.
 * - `@Column`: Customizes column name, nullability constraints, and data lengths.
 * - `@PrePersist`: Lifecycle callback that automatically timestamps the entity prior to SQL INSERT.
 */
@Entity
@Table(
    name = "scan_history",
    indexes = {
        @Index(name = "idx_scan_history_scanned_at", columnList = "scanned_at DESC"),
        @Index(name = "idx_scan_history_risk_label", columnList = "risk_label")
    }
)
public class Scan {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank(message = "Submitted URL cannot be blank")
    @Size(max = 2048, message = "URL length cannot exceed 2048 characters")
    @Column(name = "url", nullable = false, length = 2048)
    private String url;

    @NotNull(message = "Predicted class cannot be null")
    @Column(name = "predicted_class", nullable = false)
    private Integer predictedClass; // 0 = Legitimate, 1 = Phishing

    @DecimalMin(value = "0.0", message = "Confidence score must be at least 0.0")
    @DecimalMax(value = "1.0", message = "Confidence score cannot exceed 1.0")
    @Column(name = "confidence")
    private Double confidence;

    @NotBlank(message = "Risk label cannot be blank")
    @Size(max = 50, message = "Risk label cannot exceed 50 characters")
    @Column(name = "risk_label", nullable = false, length = 50)
    private String riskLabel; // e.g. "LEGITIMATE", "PHISHING", "HIGH_RISK"

    @Column(name = "scanned_at", nullable = false, updatable = false)
    private LocalDateTime scannedAt;

    @Column(name = "indicators_json", columnDefinition = "TEXT")
    private String indicatorsJson; // Serialized JSON of URL lexical indicators

    // ── Constructors ────────────────────────────────────────────────────────

    public Scan() {
        // Required by JPA specification
    }

    public Scan(String url, Integer predictedClass, Double confidence, String riskLabel) {
        this.url = url;
        this.predictedClass = predictedClass;
        this.confidence = confidence;
        this.riskLabel = riskLabel;
    }

    public Scan(String url, Integer predictedClass, Double confidence, String riskLabel, String indicatorsJson) {
        this.url = url;
        this.predictedClass = predictedClass;
        this.confidence = confidence;
        this.riskLabel = riskLabel;
        this.indicatorsJson = indicatorsJson;
    }

    // ── Lifecycle Hooks ─────────────────────────────────────────────────────

    @PrePersist
    protected void onCreate() {
        if (this.scannedAt == null) {
            this.scannedAt = LocalDateTime.now();
        }
    }

    // ── Getters and Setters ─────────────────────────────────────────────────

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    public Integer getPredictedClass() {
        return predictedClass;
    }

    public void setPredictedClass(Integer predictedClass) {
        this.predictedClass = predictedClass;
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

    public String getIndicatorsJson() {
        return indicatorsJson;
    }

    public void setIndicatorsJson(String indicatorsJson) {
        this.indicatorsJson = indicatorsJson;
    }

    // ── Object Overrides ────────────────────────────────────────────────────

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Scan scan = (Scan) o;
        return Objects.equals(id, scan.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "Scan{" +
                "id=" + id +
                ", url='" + url + '\'' +
                ", predictedClass=" + predictedClass +
                ", confidence=" + confidence +
                ", riskLabel='" + riskLabel + '\'' +
                ", scannedAt=" + scannedAt +
                '}';
    }
}

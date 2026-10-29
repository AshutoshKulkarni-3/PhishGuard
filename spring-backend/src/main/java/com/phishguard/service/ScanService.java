package com.phishguard.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.phishguard.model.Scan;
import com.phishguard.model.dto.DashboardStatsDto;
import com.phishguard.model.dto.PredictionResponse;
import com.phishguard.model.dto.ScanResultDto;
import com.phishguard.repository.ScanRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * ScanService
 * -----------
 * Core application service coordinating the scanning workflow:
 * 1. Invokes the MLService to obtain machine learning inferences.
 * 2. Persists the transaction into the MySQL `scan_history` database via ScanRepository.
 * 3. Assembles and returns the user-facing ScanResultDto.
 *
 * Annotations Explanation for AJP Viva:
 * - `@Service`: Stereotype denoting a Spring business service layer bean.
 * - `@Transactional`: Ensures database operations execute within an ACID transaction;
 *   automatically rolls back on unhandled runtime exceptions.
 */
@Service
public class ScanService {

    private static final Logger logger = LoggerFactory.getLogger(ScanService.class);

    private final MLService mlService;
    private final ScanRepository scanRepository;
    private final ObjectMapper objectMapper;

    public ScanService(MLService mlService, ScanRepository scanRepository, ObjectMapper objectMapper) {
        this.mlService = mlService;
        this.scanRepository = scanRepository;
        this.objectMapper = objectMapper;
    }

    /**
     * Scan a submitted URL end-to-end:
     * - Request prediction from ML inference service.
     * - Save audit record in scan_history.
     * - Return populated ScanResultDto.
     *
     * @param rawUrl The raw URL submitted by the client.
     * @return Complete ScanResultDto with database ID and ML indicators.
     */
    @Transactional
    public ScanResultDto scanUrl(String rawUrl) {
        String url = rawUrl.trim();
        logger.info("Processing scan request for URL: {}", url);

        // 1. Invoke Python ML service
        PredictionResponse mlResponse = mlService.predictUrl(url);

        // 2. Map ML response to Scan Entity fields
        Integer predictedClass = Boolean.TRUE.equals(mlResponse.getIsPhishing()) ? 1 : 0;
        Double confidence = mlResponse.getConfidence();
        String riskLabel = (mlResponse.getPrediction() != null)
                ? mlResponse.getPrediction().toUpperCase()
                : (predictedClass == 1 ? "PHISHING" : "LEGITIMATE");

        // Serialize indicators map into JSON text for DB storage
        String indicatorsJson = null;
        if (mlResponse.getIndicators() != null && !mlResponse.getIndicators().isEmpty()) {
            try {
                indicatorsJson = objectMapper.writeValueAsString(mlResponse.getIndicators());
            } catch (JsonProcessingException e) {
                logger.warn("Failed to serialize indicators map to JSON for URL {}: {}", url, e.getMessage());
            }
        }

        // 3. Persist record in MySQL scan_history table
        Scan scan = new Scan(url, predictedClass, confidence, riskLabel, indicatorsJson);
        Scan savedScan = scanRepository.save(scan);
        logger.info("Scan saved to database with ID: {} for URL: {}", savedScan.getId(), url);

        // 4. Construct and return response DTO
        return mapToDto(savedScan, mlResponse.getProbabilities(), mlResponse.getIndicators(), mlResponse.getDisclaimer());
    }

    /**
     * Retrieve scan history ordered from newest to oldest.
     *
     * @return List of historical scan DTOs.
     */
    @Transactional(readOnly = true)
    public List<ScanResultDto> getRecentScans() {
        return scanRepository.findAllByOrderByScannedAtDesc().stream()
                .map(this::mapEntityToDto)
                .collect(Collectors.toList());
    }

    /**
     * Retrieve a specific scan by its database primary key.
     *
     * @param id The scan record ID.
     * @return Optional containing ScanResultDto if found.
     */
    @Transactional(readOnly = true)
    public Optional<ScanResultDto> getScanById(Long id) {
        return scanRepository.findById(id).map(this::mapEntityToDto);
    }
    /**
     * Compute aggregated system and detection metrics dynamically from MySQL.
     *
     * @return DashboardStatsDto containing real counts, ratios, and latest scans.
     */
    @Transactional(readOnly = true)
    public DashboardStatsDto getDashboardStats() {
        long total = scanRepository.count();
        long phishing = scanRepository.countByPredictedClass(1);
        long legitimate = scanRepository.countByPredictedClass(0);

        double phishingRate = total > 0 ? (phishing * 100.0) / total : 0.0;
        double legitimateRate = total > 0 ? (legitimate * 100.0) / total : 0.0;

        List<ScanResultDto> recent = scanRepository.findTop10ByOrderByScannedAtDesc().stream()
                .map(this::mapEntityToDto)
                .collect(Collectors.toList());

        boolean mlOnline = mlService.checkHealth();
        String mlUrl = mlService.getMlBaseUrl();

        return new DashboardStatsDto(
                total,
                phishing,
                legitimate,
                Math.round(phishingRate * 10.0) / 10.0,
                Math.round(legitimateRate * 10.0) / 10.0,
                mlOnline,
                mlUrl,
                recent
        );
    }

    // ── Helper Mappers ──────────────────────────────────────────────────────

    private ScanResultDto mapToDto(Scan entity, Map<String, Double> probabilities,
                                   Map<String, Object> indicators, String disclaimer) {
        return new ScanResultDto(
                entity.getId(),
                entity.getUrl(),
                entity.getPredictedClass() == 1 ? "phishing" : "legitimate",
                entity.getPredictedClass() == 1,
                entity.getConfidence(),
                entity.getRiskLabel(),
                entity.getScannedAt(),
                probabilities,
                indicators,
                disclaimer
        );
    }

    @SuppressWarnings("unchecked")
    private ScanResultDto mapEntityToDto(Scan entity) {
        Map<String, Object> indicators = Collections.emptyMap();
        if (entity.getIndicatorsJson() != null && !entity.getIndicatorsJson().isBlank()) {
            try {
                indicators = objectMapper.readValue(entity.getIndicatorsJson(), Map.class);
            } catch (Exception e) {
                logger.warn("Failed to deserialize indicators_json for scan ID {}: {}", entity.getId(), e.getMessage());
            }
        }

        return new ScanResultDto(
                entity.getId(),
                entity.getUrl(),
                entity.getPredictedClass() == 1 ? "phishing" : "legitimate",
                entity.getPredictedClass() == 1,
                entity.getConfidence(),
                entity.getRiskLabel(),
                entity.getScannedAt(),
                null,
                indicators,
                null
        );
    }
}

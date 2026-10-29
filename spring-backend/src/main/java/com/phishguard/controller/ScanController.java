package com.phishguard.controller;

import com.phishguard.model.dto.DashboardStatsDto;
import com.phishguard.model.dto.PredictionRequest;
import com.phishguard.model.dto.ScanResultDto;
import com.phishguard.service.MLService;
import com.phishguard.service.ScanService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * ScanController
 * --------------
 * Spring MVC REST Controller exposing endpoints for URL scanning, dashboard stats,
 * and history retrieval.
 *
 * Annotations Explanation for AJP Viva:
 * - `@RestController`: Combines `@Controller` and `@ResponseBody`. Automatically serializes
 *   return objects directly into HTTP response JSON bodies using Jackson.
 * - `@RequestMapping("/api/scans")`: Sets the base URL path mapping for all handler methods.
 * - `@CrossOrigin`: Enables Cross-Origin Resource Sharing for modern browser frontends.
 * - `@Valid`: Triggers Jakarta Bean Validation on incoming request DTOs before executing
 *   the handler method.
 */
@RestController
@RequestMapping("/api/scans")
@CrossOrigin(origins = "*")
public class ScanController {

    private static final Logger logger = LoggerFactory.getLogger(ScanController.class);

    private final ScanService scanService;
    private final MLService mlService;

    public ScanController(ScanService scanService, MLService mlService) {
        this.scanService = scanService;
        this.mlService = mlService;
    }

    /**
     * POST /api/scans
     * Submits a URL for phishing analysis, executes ML inference, records the
     * audit in MySQL, and returns the structured scan result.
     *
     * @param request Validated PredictionRequest containing target URL.
     * @return 201 Created with populated ScanResultDto.
     */
    @PostMapping
    public ResponseEntity<ScanResultDto> createScan(@Valid @RequestBody PredictionRequest request) {
        logger.info("Received URL scan request: {}", request.getUrl());
        ScanResultDto result = scanService.scanUrl(request.getUrl());
        return ResponseEntity.status(HttpStatus.CREATED).body(result);
    }

    /**
     * GET /api/scans
     * Retrieves all historical scan records ordered from newest to oldest.
     *
     * @return 200 OK with list of ScanResultDto records.
     */
    @GetMapping
    public ResponseEntity<List<ScanResultDto>> getAllScans() {
        List<ScanResultDto> scans = scanService.getRecentScans();
        return ResponseEntity.ok(scans);
    }

    /**
     * GET /api/scans/{id}
     * Retrieves a single historical scan record by its ID.
     *
     * @param id The scan ID.
     * @return 200 OK with ScanResultDto if found, or 404 Not Found.
     */
    @GetMapping("/{id}")
    public ResponseEntity<ScanResultDto> getScanById(@PathVariable Long id) {
        return scanService.getScanById(id)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).build());
    }

    /**
     * GET /api/scans/dashboard
     * Retrieves aggregated system metrics, detection counts, and recent activity.
     *
     * @return 200 OK with DashboardStatsDto.
     */
    @GetMapping("/dashboard")
    public ResponseEntity<DashboardStatsDto> getDashboardStats() {
        DashboardStatsDto stats = scanService.getDashboardStats();
        return ResponseEntity.ok(stats);
    }

    /**
     * GET /api/scans/status
     * Diagnostic probe checking Spring Boot and downstream Python ML service health.
     *
     * @return 200 OK with health status map.
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getSystemStatus() {
        boolean mlHealthy = mlService.checkHealth();
        Map<String, Object> status = new HashMap<>();
        status.put("backend", "UP");
        status.put("mlService", mlHealthy ? "UP" : "DOWN");
        status.put("mlServiceUrl", mlService.getMlBaseUrl());
        return ResponseEntity.ok(status);
    }
}

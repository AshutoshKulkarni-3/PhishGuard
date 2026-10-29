package com.phishguard.service;

import com.phishguard.model.dto.PredictionRequest;
import com.phishguard.model.dto.PredictionResponse;
import com.phishguard.exception.MLServiceException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

/**
 * MLService
 * ---------
 * HTTP Client service responsible for communicating with the Python Flask ML Service.
 *
 * Responsibilities:
 * - Dispatches URL prediction requests to Flask `POST /predict`.
 * - Handles connection timeouts, network partitions, and 4xx/5xx HTTP responses.
 * - Deserializes the JSON prediction payload into `PredictionResponse`.
 * - Provides a health check probe against Flask `GET /health`.
 */
@Service
public class MLService {

    private static final Logger logger = LoggerFactory.getLogger(MLService.class);

    private final RestClient restClient;
    private final String mlBaseUrl;
    private final String predictEndpoint;
    private final String healthEndpoint;

    @org.springframework.beans.factory.annotation.Autowired
    public MLService(
            RestClient.Builder restClientBuilder,
            @Value("${phishguard.ml-service.url:http://localhost:5050}") String mlBaseUrl,
            @Value("${phishguard.ml-service.predict-endpoint:/predict}") String predictEndpoint,
            @Value("${phishguard.ml-service.health-endpoint:/health}") String healthEndpoint,
            @Value("${phishguard.ml-service.connect-timeout-ms:3000}") int connectTimeoutMs,
            @Value("${phishguard.ml-service.read-timeout-ms:5000}") int readTimeoutMs) {

        this.mlBaseUrl = mlBaseUrl.replaceAll("/+$", "");
        this.predictEndpoint = predictEndpoint.startsWith("/") ? predictEndpoint : "/" + predictEndpoint;
        this.healthEndpoint = healthEndpoint.startsWith("/") ? healthEndpoint : "/" + healthEndpoint;

        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeoutMs);
        requestFactory.setReadTimeout(readTimeoutMs);

        this.restClient = restClientBuilder
                .baseUrl(this.mlBaseUrl)
                .requestFactory(requestFactory)
                .build();

        logger.info("MLService initialized targeting: {}{} (Connect timeout: {}ms, Read timeout: {}ms)",
                this.mlBaseUrl, this.predictEndpoint, connectTimeoutMs, readTimeoutMs);
    }

    /**
     * Testing constructor allowing pre-configured or mocked RestClient.
     */
    public MLService(
            RestClient restClient,
            String mlBaseUrl,
            String predictEndpoint,
            String healthEndpoint) {
        this.restClient = restClient;
        this.mlBaseUrl = mlBaseUrl.replaceAll("/+$", "");
        this.predictEndpoint = predictEndpoint.startsWith("/") ? predictEndpoint : "/" + predictEndpoint;
        this.healthEndpoint = healthEndpoint.startsWith("/") ? healthEndpoint : "/" + healthEndpoint;
    }

    /**
     * Submit a URL to the Python Flask ML service for real-time inference.
     *
     * @param url The target website URL to evaluate.
     * @return Deserialized PredictionResponse DTO.
     * @throws MLServiceException if the service is unreachable, times out, or errors.
     */
    public PredictionResponse predictUrl(String url) {
        String targetUri = this.predictEndpoint;
        logger.debug("Dispatching prediction request to {}{} for URL: {}", this.mlBaseUrl, targetUri, url);

        try {
            PredictionResponse response = restClient.post()
                    .uri(targetUri)
                    .contentType(MediaType.APPLICATION_JSON)
                    .accept(MediaType.APPLICATION_JSON)
                    .body(new PredictionRequest(url))
                    .retrieve()
                    .body(PredictionResponse.class);

            if (response == null || response.getPrediction() == null) {
                logger.error("ML service returned an empty or malformed prediction body for URL: {}", url);
                throw new MLServiceException("ML service returned an invalid or empty response payload.");
            }

            logger.info("Received prediction for '{}': outcome='{}', isPhishing={}, confidence={}",
                    url, response.getPrediction(), response.getIsPhishing(), response.getConfidence());
            return response;

        } catch (ResourceAccessException e) {
            logger.error("Failed to connect to ML service at {}{}: {}", this.mlBaseUrl, targetUri, e.getMessage());
            throw new MLServiceException("ML inference service is currently offline or timed out: " + e.getMessage(), e);

        } catch (HttpClientErrorException e) {
            logger.warn("ML service rejected request with client error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new MLServiceException("ML service rejected the request: " + e.getResponseBodyAsString(), e.getStatusCode().value());

        } catch (HttpServerErrorException e) {
            logger.error("ML service failed with server error {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new MLServiceException("ML service encountered an internal error. Please try again later.", 502);

        } catch (Exception e) {
            logger.error("Unexpected error occurred while invoking ML service: {}", e.getMessage(), e);
            throw new MLServiceException("Unexpected failure during ML service communication: " + e.getMessage(), e);
        }
    }

    /**
     * Probe the Python Flask ML service health endpoint.
     *
     * @return true if the service responds 200 OK, false otherwise.
     */
    public boolean checkHealth() {
        try {
            restClient.get()
                    .uri(this.healthEndpoint)
                    .retrieve()
                    .toBodilessEntity();
            return true;
        } catch (Exception e) {
            logger.warn("ML service health probe failed at {}{}: {}", this.mlBaseUrl, this.healthEndpoint, e.getMessage());
            return false;
        }
    }

    public String getMlBaseUrl() {
        return mlBaseUrl;
    }
}

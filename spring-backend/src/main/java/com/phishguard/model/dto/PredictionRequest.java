package com.phishguard.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * PredictionRequest
 * -----------------
 * DTO carrying the target website URL from the client to Spring Boot,
 * and subsequently forwarded to the Python Flask ML service.
 */
public class PredictionRequest {

    @NotBlank(message = "URL cannot be blank or empty")
    @Size(max = 2048, message = "URL cannot exceed 2048 characters")
    @Pattern(
        regexp = "^(https?://)?[a-zA-Z0-9][-a-zA-Z0-9.]*(:[0-9]+)?(/[^\\s]*)?$",
        message = "Submitted string is not a valid URL or hostname format"
    )
    private String url;

    public PredictionRequest() {
    }

    public PredictionRequest(String url) {
        this.url = url;
    }

    public String getUrl() {
        return url;
    }

    public void setUrl(String url) {
        this.url = url;
    }

    @Override
    public String toString() {
        return "PredictionRequest{url='" + url + "'}";
    }
}

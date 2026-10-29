package com.phishguard.exception;

/**
 * MLServiceException
 * ------------------
 * Thrown when the external Python Flask ML service is unreachable,
 * times out, or returns an unprocessable response.
 */
public class MLServiceException extends RuntimeException {

    private final int statusCode;

    public MLServiceException(String message) {
        super(message);
        this.statusCode = 503; // Service Unavailable
    }

    public MLServiceException(String message, Throwable cause) {
        super(message, cause);
        this.statusCode = 503;
    }

    public MLServiceException(String message, int statusCode) {
        super(message);
        this.statusCode = statusCode;
    }

    public int getStatusCode() {
        return statusCode;
    }
}

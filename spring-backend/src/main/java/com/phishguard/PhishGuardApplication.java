package com.phishguard;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.core.env.Environment;

/**
 * PhishGuardApplication
 * ---------------------
 * Main entry point for the PhishGuard Spring Boot backend application.
 *
 * Responsibilities:
 * - Bootstraps the Spring ApplicationContext.
 * - Activates Spring Boot auto-configuration.
 * - Triggers component scanning within package `com.phishguard`.
 */
@SpringBootApplication
public class PhishGuardApplication {

    private static final Logger logger = LoggerFactory.getLogger(PhishGuardApplication.class);

    public static void main(String[] args) {
        // Automatically load .env file if present in working directory
        loadDotenv();

        SpringApplication app = new SpringApplication(PhishGuardApplication.class);
        Environment env = app.run(args).getEnvironment();

        String port = env.getProperty("server.port", "8080");
        String mlUrl = env.getProperty("phishguard.ml-service.url", "http://localhost:5000");
        String dbUrl = env.getProperty("spring.datasource.url", "(not configured)");

        logger.info("=================================================================");
        logger.info("  PhishGuard Spring Boot Backend Initialized Successfully!");
        logger.info("  Local Web Server Port : {}", port);
        logger.info("  Connected ML Service  : {}", mlUrl);
        logger.info("  Configured Database   : {}", dbUrl);
        logger.info("=================================================================");
    }

    /**
     * Reads a local .env file (if present) and registers properties into System properties
     * so Spring Boot can resolve ${DB_PASSWORD}, ${DB_USER}, etc. without manual shell exports.
     */
    private static void loadDotenv() {
        java.io.File[] candidateFiles = {
            new java.io.File(".env"),
            new java.io.File("spring-backend/.env"),
            new java.io.File("../.env")
        };

        for (java.io.File envFile : candidateFiles) {
            if (envFile.exists() && envFile.isFile()) {
                try (java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.FileReader(envFile))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        line = line.trim();
                        if (line.isEmpty() || line.startsWith("#")) {
                            continue;
                        }
                        int eqIdx = line.indexOf('=');
                        if (eqIdx > 0) {
                            String key = line.substring(0, eqIdx).trim();
                            String val = line.substring(eqIdx + 1).trim();
                            if ((val.startsWith("\"") && val.endsWith("\"")) || (val.startsWith("'") && val.endsWith("'"))) {
                                val = val.substring(1, val.length() - 1);
                            }
                            if (System.getProperty(key) == null && System.getenv(key) == null) {
                                System.setProperty(key, val);
                            }
                        }
                    }
                    logger.info("Loaded environment variables from: {}", envFile.getAbsolutePath());
                    break;
                } catch (Exception e) {
                    logger.warn("Could not read .env file at {}: {}", envFile.getPath(), e.getMessage());
                }
            }
        }
    }
}

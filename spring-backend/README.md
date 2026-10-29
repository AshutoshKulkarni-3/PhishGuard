# PhishGuard — Spring Boot Backend (MVC Architecture)

> Modern Java & Spring Boot backend service for the **PhishGuard** phishing website detection system.  
> Stack: **Java 21 · Spring Boot 3.3.4 · Spring Data JPA · Hibernate 6 · MySQL · Vanilla HTML/CSS/JS**

---

## 1. MVC Architecture & Directory Structure

PhishGuard implements the clean **Model-View-Controller (MVC)** architectural pattern:

```
spring-backend/
├── pom.xml                               # Maven build configuration & dependencies
├── mvnw / mvnw.cmd                       # Maven wrappers
├── .env                                  # Environment variables configuration
├── README.md                             # Backend documentation
└── src/
    └── main/
        ├── java/
        │   └── com/phishguard/
        │       ├── PhishGuardApplication.java   # Spring Boot entry point
        │       │
        │       ├── controller/                  # [CONTROLLER in MVC]
        │       │   └── ScanController.java      # REST API endpoints (/api/scans)
        │       │
        │       ├── model/                       # [MODEL in MVC]
        │       │   ├── Scan.java                # JPA Entity mapped to MySQL scan_history table
        │       │   └── dto/                     # Data Transfer Objects
        │       │       ├── PredictionRequest.java
        │       │       ├── PredictionResponse.java
        │       │       ├── ScanResultDto.java
        │       │       └── DashboardStatsDto.java
        │       │
        │       ├── service/                     # [BUSINESS SERVICE LAYER]
        │       │   ├── ScanService.java         # Scanning workflow orchestrator
        │       │   └── MLService.java           # HTTP client to Flask ML microservice
        │       │
        │       ├── repository/                  # [DATA ACCESS LAYER]
        │       │   └── ScanRepository.java      # Spring Data JPA repository
        │       │
        │       └── exception/                   # [CENTRAL EXCEPTION HANDLING]
        │           ├── GlobalExceptionHandler.java
        │           └── MLServiceException.java
        │
        └── resources/
            ├── application.properties           # Spring Boot configuration
            └── static/                          # [VIEW in MVC - Minimal Single-Page UI]
                ├── index.html                   # Clean, lightweight frontend layout
                ├── css/
                │   └── style.css                # Minimal, modern vanilla CSS
                └── js/
                    └── app.js                   # Client-side JavaScript communicating with REST API
```

---

## 2. Dependencies & Architectural Purpose

All dependencies in [`pom.xml`](pom.xml) serve dedicated architectural roles without unnecessary bloat:

| Dependency | Artifact Coordinates | Architectural Purpose |
| :--- | :--- | :--- |
| **Spring Web / Spring MVC** | `spring-boot-starter-web` | Provides REST controllers, HTTP request handling, JSON serialization (Jackson), and embedded Apache Tomcat. |
| **Spring Data JPA** | `spring-boot-starter-data-jpa` | Provides CRUD repository abstractions, automatic SQL generation, and transaction management. |
| **Hibernate ORM** | *(included transitively)* | JPA implementation that maps the `Scan` entity model to MySQL relational tables. |
| **MySQL Connector/J** | `com.mysql:mysql-connector-j` | Official JDBC driver enabling high-throughput connection pooling via HikariCP. |
| **Jakarta Validation** | `spring-boot-starter-validation` | Bean Validation for verifying incoming URLs before processing (`@NotBlank`, `@Size`, `@Pattern`). |

---

## 3. REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/scans` | Submit target URL for ML analysis and persist result to MySQL |
| `GET` | `/api/scans` | Retrieve recent scan history records |
| `GET` | `/api/scans/{id}` | Retrieve specific scan record by ID |
| `GET` | `/api/scans/dashboard` | Retrieve aggregated dashboard statistics (total, phishing, safe) |
| `GET` | `/api/scans/status` | Diagnostic health probe for Spring Boot backend & Python ML service |

---

## 4. Environment Configuration

All parameters are externalized in `.env` and `application.properties`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SERVER_PORT` | `8081` | Port for the embedded web server |
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | `phishguard_db` | MySQL database name |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | `Ashutosh@3` | MySQL password |
| `ML_SERVICE_URL` | `http://localhost:5050` | Python Flask inference service URL |

---

## 5. Execution Commands

### 1. Build Executable JAR
```bash
./mvnw clean package
```

### 2. Run the Spring Boot Application
```bash
./mvnw spring-boot:run
```

Once started, open **`http://localhost:8081/`** in your browser to view the clean, minimal web UI.

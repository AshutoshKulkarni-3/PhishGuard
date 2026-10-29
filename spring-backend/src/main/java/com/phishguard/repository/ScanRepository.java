package com.phishguard.repository;

import com.phishguard.model.Scan;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * ScanRepository
 * --------------
 * Spring Data JPA repository for managing `Scan` entities in the `scan_history` table.
 *
 * Annotations & Spring Data JPA Concepts for AJP Viva:
 * - `@Repository`: Spring component stereotype that marks this interface as a Data Access Object (DAO)
 *   and enables Spring's automatic exception translation (converting low-level SQLExceptions into
 *   Spring's DataAccessException hierarchy).
 * - `JpaRepository<Scan, Long>`: Inherits standard CRUD operations (`save`, `findById`, `delete`,
 *   `count`, `flush`) as well as pagination and sorting capabilities without writing raw SQL.
 * - Derived Query Methods: Spring Data analyzes method names (e.g., `findAllByOrderByScannedAtDesc`)
 *   at startup and automatically synthesizes the underlying JPQL and SQL queries.
 */
@Repository
public interface ScanRepository extends JpaRepository<Scan, Long> {

    /**
     * Retrieve all historical scans ordered by scan timestamp in descending order (most recent first).
     *
     * @return List of scans ordered newest to oldest.
     */
    List<Scan> findAllByOrderByScannedAtDesc();

    /**
     * Paginated retrieval of scans ordered by scan timestamp in descending order.
     * Essential for UI table pagination without loading the entire history into memory.
     *
     * @param pageable Pagination and sorting criteria.
     * @return Page of scans.
     */
    Page<Scan> findAllByOrderByScannedAtDesc(Pageable pageable);

    /**
     * Retrieve the latest N scans for quick dashboard preview widgets.
     *
     * @return Top 10 most recent scans.
     */
    List<Scan> findTop10ByOrderByScannedAtDesc();

    /**
     * Filter scans by risk label (e.g., "PHISHING" vs "LEGITIMATE") in descending order.
     *
     * @param riskLabel The classification label filter.
     * @return List of matching scans.
     */
    List<Scan> findByRiskLabelOrderByScannedAtDesc(String riskLabel);

    /**
     * Retrieve scans conducted within a specific time window.
     *
     * @param start Window start time.
     * @param end   Window end time.
     * @return List of scans in range.
     */
    List<Scan> findByScannedAtBetweenOrderByScannedAtDesc(LocalDateTime start, LocalDateTime end);

    /**
     * Count total scans grouped by predicted class (0 = legitimate, 1 = phishing).
     *
     * @param predictedClass The binary prediction class.
     * @return Count of occurrences.
     */
    long countByPredictedClass(Integer predictedClass);
}

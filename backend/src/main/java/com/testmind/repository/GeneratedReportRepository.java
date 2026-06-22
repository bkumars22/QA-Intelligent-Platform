package com.testmind.repository;

import com.testmind.model.GeneratedReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface GeneratedReportRepository extends JpaRepository<GeneratedReport, Long> {
    List<GeneratedReport> findByProjectIdOrderByCreatedAtDesc(Long projectId);
    Optional<GeneratedReport> findByShareToken(String shareToken);
    Optional<GeneratedReport> findByExecutionId(Long executionId);
}

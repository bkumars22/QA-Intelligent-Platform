package com.testmind.repository;

import com.testmind.model.AutomationResult;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AutomationResultRepository extends JpaRepository<AutomationResult, Long> {
    List<AutomationResult> findByExecutionIdOrderByCreatedAtAsc(Long executionId);
    List<AutomationResult> findByExecutionIdAndStatus(Long executionId, String status);
    long countByExecutionIdAndStatus(Long executionId, String status);
}

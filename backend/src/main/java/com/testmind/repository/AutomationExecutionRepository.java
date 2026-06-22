package com.testmind.repository;

import com.testmind.model.AutomationExecution;
import com.testmind.model.AutomationStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface AutomationExecutionRepository extends JpaRepository<AutomationExecution, Long> {
    List<AutomationExecution> findByProjectIdOrderByCreatedAtDesc(Long projectId);
    List<AutomationExecution> findByStatusIn(List<AutomationStatus> statuses);
    List<AutomationExecution> findTop20ByOrderByCreatedAtDesc();
}

package com.testmind.repository;

import com.testmind.model.PerformanceTestResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PerformanceTestResultRepository extends JpaRepository<PerformanceTestResult, Long> {

    List<PerformanceTestResult> findBySystemOrderByTestedAtDesc(String system);
}

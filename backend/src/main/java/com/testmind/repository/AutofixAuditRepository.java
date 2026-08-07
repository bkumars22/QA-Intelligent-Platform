package com.testmind.repository;

import com.testmind.model.AutofixAudit;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AutofixAuditRepository extends JpaRepository<AutofixAudit, Long> {

    List<AutofixAudit> findByProjectIdOrderByCreatedAtDesc(Long projectId);

    List<AutofixAudit> findByStatusOrderByCreatedAtDesc(String status);

    List<AutofixAudit> findByProjectIdAndStatusOrderByCreatedAtDesc(Long projectId, String status);

    List<AutofixAudit> findAllByOrderByCreatedAtDesc();
}

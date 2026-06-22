package com.testmind.repository;

import com.testmind.model.FrameworkProfile;
import com.testmind.model.FrameworkType;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface FrameworkProfileRepository extends JpaRepository<FrameworkProfile, Long> {
    List<FrameworkProfile> findByProjectId(Long projectId);
    Optional<FrameworkProfile> findByProjectIdAndFrameworkType(Long projectId, FrameworkType type);
}

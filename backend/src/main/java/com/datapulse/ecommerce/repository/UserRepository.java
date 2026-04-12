package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.entity.enums.Role;
import org.springframework.data.jpa.repository.JpaRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    boolean existsByEmail(String email);
    List<User> findByRole(Role role);
    List<User> findByEnabled(Boolean enabled);
    long countByRole(Role role);
    long countByCreatedAtAfter(LocalDateTime after);
}

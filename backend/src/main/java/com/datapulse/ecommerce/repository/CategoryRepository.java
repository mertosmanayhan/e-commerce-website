package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.Category;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface CategoryRepository extends JpaRepository<Category, Long> {
    Optional<Category> findByName(String name);
    List<Category> findByParentCategoryIsNull();
    boolean existsByName(String name);
}

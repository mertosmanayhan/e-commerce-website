package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.Store;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface StoreRepository extends JpaRepository<Store, Long> {
    List<Store> findByOwnerId(Long ownerId);
    List<Store> findByIsOpen(Boolean isOpen);
}

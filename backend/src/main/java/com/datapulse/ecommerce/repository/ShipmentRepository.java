package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.Shipment;
import com.datapulse.ecommerce.entity.enums.ShipmentStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface ShipmentRepository extends JpaRepository<Shipment, Long> {
    Optional<Shipment> findByOrderId(Long orderId);
    List<Shipment> findByStatus(ShipmentStatus status);
    Optional<Shipment> findByTrackingNumber(String trackingNumber);
}

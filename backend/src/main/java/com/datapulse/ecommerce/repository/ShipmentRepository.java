package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.Shipment;
import com.datapulse.ecommerce.entity.enums.ShipmentStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.List;
import java.util.Optional;

public interface ShipmentRepository extends JpaRepository<Shipment, Long> {
    Optional<Shipment> findByOrderId(Long orderId);
    List<Shipment> findByStatus(ShipmentStatus status);
    Optional<Shipment> findByTrackingNumber(String trackingNumber);

    // Bireysel kullanıcının siparişlerine ait kargolar
    @Query("SELECT s FROM Shipment s WHERE s.order.user.id = :userId")
    List<Shipment> findByUserId(@Param("userId") Long userId);

    // Corporate: kendi mağazasının ürünlerini içeren siparişlerin kargoları
    @Query("SELECT DISTINCT s FROM Shipment s JOIN s.order o JOIN o.items oi JOIN oi.product p WHERE p.store.owner.id = :ownerId")
    List<Shipment> findByStoreOwnerId(@Param("ownerId") Long ownerId);
}

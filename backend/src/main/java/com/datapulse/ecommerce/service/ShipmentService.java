package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.entity.Shipment;
import com.datapulse.ecommerce.entity.enums.ShipmentStatus;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.ShipmentRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class ShipmentService {
    private final ShipmentRepository shipmentRepository;
    public ShipmentService(ShipmentRepository sr) { this.shipmentRepository = sr; }

    public List<Shipment> getAllShipments() { return shipmentRepository.findAll(); }
    public Shipment getShipmentByOrderId(Long orderId) { return shipmentRepository.findByOrderId(orderId).orElseThrow(() -> new ResourceNotFoundException("Shipment","orderId",orderId)); }
    public Shipment getShipmentByTrackingNumber(String tn) { return shipmentRepository.findByTrackingNumber(tn).orElseThrow(() -> new ResourceNotFoundException("Shipment","trackingNumber",tn)); }

    @Transactional public Shipment updateShipmentStatus(Long id, String status) {
        Shipment s = shipmentRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Shipment","id",id));
        ShipmentStatus ns = ShipmentStatus.valueOf(status.toUpperCase()); s.setStatus(ns);
        if (ns == ShipmentStatus.IN_TRANSIT && s.getShippedDate()==null) s.setShippedDate(LocalDateTime.now());
        if (ns == ShipmentStatus.DELIVERED && s.getDeliveryDate()==null) s.setDeliveryDate(LocalDateTime.now());
        return shipmentRepository.save(s);
    }
}

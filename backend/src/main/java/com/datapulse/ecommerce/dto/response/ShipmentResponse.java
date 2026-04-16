package com.datapulse.ecommerce.dto.response;

import com.datapulse.ecommerce.entity.Shipment;
import com.datapulse.ecommerce.entity.enums.ShipmentStatus;
import java.time.LocalDateTime;

public class ShipmentResponse {
    private Long id;
    private String trackingNumber;
    private ShipmentStatus status;
    private String modeOfShipment;
    private String carrier;
    private LocalDateTime shippedDate;
    private LocalDateTime deliveryDate;
    private LocalDateTime createdAt;

    // Sipariş bilgileri
    private Long orderId;
    private String orderNumber;
    private LocalDateTime orderDate;

    // Müşteri bilgileri
    private String customerName;
    private String customerEmail;

    public static ShipmentResponse fromEntity(Shipment s) {
        ShipmentResponse res = new ShipmentResponse();
        res.id = s.getId();
        res.trackingNumber = s.getTrackingNumber();
        res.status = s.getStatus();
        res.modeOfShipment = s.getModeOfShipment();
        res.carrier = s.getModeOfShipment(); // modeOfShipment aynı zamanda carrier
        res.shippedDate = s.getShippedDate();
        res.deliveryDate = s.getDeliveryDate();

        if (s.getOrder() != null) {
            res.orderId = s.getOrder().getId();
            res.orderNumber = s.getOrder().getOrderNumber();
            res.orderDate = s.getOrder().getOrderDate();
            res.createdAt = s.getOrder().getOrderDate();
            if (s.getOrder().getUser() != null) {
                res.customerName = s.getOrder().getUser().getFullName();
                res.customerEmail = s.getOrder().getUser().getEmail();
            }
        }
        return res;
    }

    public Long getId() { return id; }
    public String getTrackingNumber() { return trackingNumber; }
    public ShipmentStatus getStatus() { return status; }
    public String getModeOfShipment() { return modeOfShipment; }
    public String getCarrier() { return carrier; }
    public LocalDateTime getShippedDate() { return shippedDate; }
    public LocalDateTime getDeliveryDate() { return deliveryDate; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getOrderId() { return orderId; }
    public String getOrderNumber() { return orderNumber; }
    public LocalDateTime getOrderDate() { return orderDate; }
    public String getCustomerName() { return customerName; }
    public String getCustomerEmail() { return customerEmail; }
}

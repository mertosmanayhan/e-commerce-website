package com.datapulse.ecommerce.entity;

import com.datapulse.ecommerce.entity.enums.OrderStatus;
import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "orders", indexes = {
    @Index(name = "idx_order_user", columnList = "user_id"),
    @Index(name = "idx_order_status", columnList = "status"),
    @Index(name = "idx_order_date", columnList = "orderDate")
})
public class Order {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(nullable = false, unique = true) private String orderNumber;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "user_id", nullable = false) private User user;
    @Enumerated(EnumType.STRING) @Column(nullable = false) private OrderStatus status;
    @Column(nullable = false, precision = 12, scale = 2) private BigDecimal totalAmount;
    private String paymentMethod;
    private String fulfilment;
    private String salesChannel;
    @Column(nullable = false) private LocalDateTime orderDate;
    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();
    @OneToOne(mappedBy = "order", cascade = CascadeType.ALL) @JsonIgnore
    private Shipment shipment;

    public Order() {}
    @PrePersist protected void onCreate() {
        if (this.orderDate == null) this.orderDate = LocalDateTime.now();
        if (this.status == null) this.status = OrderStatus.PENDING;
    }

    public Long getId() { return id; } public void setId(Long id) { this.id = id; }
    public String getOrderNumber() { return orderNumber; } public void setOrderNumber(String v) { this.orderNumber = v; }
    public User getUser() { return user; } public void setUser(User v) { this.user = v; }
    public OrderStatus getStatus() { return status; } public void setStatus(OrderStatus v) { this.status = v; }
    public BigDecimal getTotalAmount() { return totalAmount; } public void setTotalAmount(BigDecimal v) { this.totalAmount = v; }
    public String getPaymentMethod() { return paymentMethod; } public void setPaymentMethod(String v) { this.paymentMethod = v; }
    public String getFulfilment() { return fulfilment; } public void setFulfilment(String v) { this.fulfilment = v; }
    public String getSalesChannel() { return salesChannel; } public void setSalesChannel(String v) { this.salesChannel = v; }
    public LocalDateTime getOrderDate() { return orderDate; } public void setOrderDate(LocalDateTime v) { this.orderDate = v; }
    public List<OrderItem> getItems() { return items; } public void setItems(List<OrderItem> v) { this.items = v; }
    public Shipment getShipment() { return shipment; } public void setShipment(Shipment v) { this.shipment = v; }

    public static OrderBuilder builder() { return new OrderBuilder(); }
    public static class OrderBuilder {
        private String orderNumber, paymentMethod; private User user; private OrderStatus status;
        private BigDecimal totalAmount; private LocalDateTime orderDate; private List<OrderItem> items = new ArrayList<>();
        public OrderBuilder orderNumber(String v) { this.orderNumber = v; return this; }
        public OrderBuilder user(User v) { this.user = v; return this; }
        public OrderBuilder status(OrderStatus v) { this.status = v; return this; }
        public OrderBuilder totalAmount(BigDecimal v) { this.totalAmount = v; return this; }
        public OrderBuilder paymentMethod(String v) { this.paymentMethod = v; return this; }
        public OrderBuilder orderDate(LocalDateTime v) { this.orderDate = v; return this; }
        public OrderBuilder items(List<OrderItem> v) { this.items = v; return this; }
        public Order build() {
            Order o = new Order(); o.orderNumber=orderNumber; o.user=user; o.status=status;
            o.totalAmount=totalAmount; o.paymentMethod=paymentMethod; o.orderDate=orderDate; o.items=items;
            return o;
        }
    }
}

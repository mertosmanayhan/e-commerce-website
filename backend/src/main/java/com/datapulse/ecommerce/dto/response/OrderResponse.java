package com.datapulse.ecommerce.dto.response;

import com.datapulse.ecommerce.entity.Order;
import com.datapulse.ecommerce.entity.OrderItem;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

public class OrderResponse {
    private Long id, customerId; private String orderNumber, status, paymentMethod, customerName;
    private BigDecimal totalAmount; private LocalDateTime orderDate; private List<OrderItemResponse> items;

    public Long getId() { return id; } public String getOrderNumber() { return orderNumber; }
    public String getStatus() { return status; } public BigDecimal getTotalAmount() { return totalAmount; }
    public String getPaymentMethod() { return paymentMethod; } public LocalDateTime getOrderDate() { return orderDate; }
    public String getCustomerName() { return customerName; } public Long getCustomerId() { return customerId; }
    public List<OrderItemResponse> getItems() { return items; }

    public static class OrderItemResponse {
        private Long id, productId; private String productName, productSku, imageUrl;
        private Integer quantity; private BigDecimal unitPrice, subtotal;
        public Long getId() { return id; } public Long getProductId() { return productId; }
        public String getProductName() { return productName; } public String getProductSku() { return productSku; }
        public String getImageUrl() { return imageUrl; }
        public Integer getQuantity() { return quantity; } public BigDecimal getUnitPrice() { return unitPrice; }
        public BigDecimal getSubtotal() { return subtotal; }
        public static OrderItemResponse fromEntity(OrderItem i) {
            OrderItemResponse r = new OrderItemResponse();
            r.id=i.getId(); r.productId=i.getProduct().getId(); r.productName=i.getProduct().getName();
            r.productSku=i.getProduct().getSku(); r.quantity=i.getQuantity(); r.unitPrice=i.getUnitPrice();
            r.subtotal=i.getUnitPrice().multiply(BigDecimal.valueOf(i.getQuantity()));
            r.imageUrl=i.getProduct().getImageUrl();
            return r;
        }
    }

    public static OrderResponse fromEntity(Order o) {
        OrderResponse r = new OrderResponse();
        r.id=o.getId(); r.orderNumber=o.getOrderNumber(); r.status=o.getStatus().name();
        r.totalAmount=o.getTotalAmount(); r.paymentMethod=o.getPaymentMethod(); r.orderDate=o.getOrderDate();
        r.customerName=o.getUser().getFullName(); r.customerId=o.getUser().getId();
        r.items = o.getItems()!=null ? o.getItems().stream().map(OrderItemResponse::fromEntity).toList() : List.of();
        return r;
    }
}

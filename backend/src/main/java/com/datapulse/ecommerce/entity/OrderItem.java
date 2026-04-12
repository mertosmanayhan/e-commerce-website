package com.datapulse.ecommerce.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Table(name = "order_items")
public class OrderItem {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "order_id", nullable = false) @JsonIgnore
    private Order order;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "product_id", nullable = false)
    private Product product;
    @Column(nullable = false) private Integer quantity;
    @Column(nullable = false, precision = 10, scale = 2) private BigDecimal unitPrice;

    public OrderItem() {}
    public Long getId() { return id; } public void setId(Long id) { this.id = id; }
    public Order getOrder() { return order; } public void setOrder(Order v) { this.order = v; }
    public Product getProduct() { return product; } public void setProduct(Product v) { this.product = v; }
    public Integer getQuantity() { return quantity; } public void setQuantity(Integer v) { this.quantity = v; }
    public BigDecimal getUnitPrice() { return unitPrice; } public void setUnitPrice(BigDecimal v) { this.unitPrice = v; }

    public static OrderItemBuilder builder() { return new OrderItemBuilder(); }
    public static class OrderItemBuilder {
        private Order order; private Product product; private Integer quantity; private BigDecimal unitPrice;
        public OrderItemBuilder order(Order v) { this.order = v; return this; }
        public OrderItemBuilder product(Product v) { this.product = v; return this; }
        public OrderItemBuilder quantity(Integer v) { this.quantity = v; return this; }
        public OrderItemBuilder unitPrice(BigDecimal v) { this.unitPrice = v; return this; }
        public OrderItem build() { OrderItem i = new OrderItem(); i.order=order; i.product=product; i.quantity=quantity; i.unitPrice=unitPrice; return i; }
    }
}

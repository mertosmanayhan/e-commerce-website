package com.datapulse.ecommerce.dto.request;
import java.util.List;
public class CreateOrderRequest {
    private String paymentMethod;
    private List<OrderItemRequest> items;
    public String getPaymentMethod() { return paymentMethod; } public void setPaymentMethod(String v) { this.paymentMethod = v; }
    public List<OrderItemRequest> getItems() { return items; } public void setItems(List<OrderItemRequest> v) { this.items = v; }
    public static class OrderItemRequest {
        private Long productId; private Integer quantity;
        public Long getProductId() { return productId; } public void setProductId(Long v) { this.productId = v; }
        public Integer getQuantity() { return quantity; } public void setQuantity(Integer v) { this.quantity = v; }
    }
}

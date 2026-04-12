package com.datapulse.ecommerce.dto.response;

import java.math.BigDecimal;

public class CartItemResponse {
    private Long id, productId; private String productName, productSku, imageUrl;
    private BigDecimal price; private Integer quantity;

    public Long getId() { return id; } public void setId(Long v) { this.id = v; }
    public Long getProductId() { return productId; } public void setProductId(Long v) { this.productId = v; }
    public String getProductName() { return productName; } public void setProductName(String v) { this.productName = v; }
    public String getProductSku() { return productSku; } public void setProductSku(String v) { this.productSku = v; }
    public String getImageUrl() { return imageUrl; } public void setImageUrl(String v) { this.imageUrl = v; }
    public BigDecimal getPrice() { return price; } public void setPrice(BigDecimal v) { this.price = v; }
    public Integer getQuantity() { return quantity; } public void setQuantity(Integer v) { this.quantity = v; }
}

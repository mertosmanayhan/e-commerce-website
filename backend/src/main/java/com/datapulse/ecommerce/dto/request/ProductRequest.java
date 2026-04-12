package com.datapulse.ecommerce.dto.request;
import java.math.BigDecimal;
public class ProductRequest {
    private String name, description, sku, imageUrl; private BigDecimal price; private Integer stock; private Long categoryId, storeId;
    public String getName() { return name; } public void setName(String v) { this.name = v; }
    public String getDescription() { return description; } public void setDescription(String v) { this.description = v; }
    public String getSku() { return sku; } public void setSku(String v) { this.sku = v; }
    public BigDecimal getPrice() { return price; } public void setPrice(BigDecimal v) { this.price = v; }
    public Integer getStock() { return stock; } public void setStock(Integer v) { this.stock = v; }
    public Long getCategoryId() { return categoryId; } public void setCategoryId(Long v) { this.categoryId = v; }
    public Long getStoreId() { return storeId; } public void setStoreId(Long v) { this.storeId = v; }
    public String getImageUrl() { return imageUrl; } public void setImageUrl(String v) { this.imageUrl = v; }
}

package com.datapulse.ecommerce.dto.response;

import com.datapulse.ecommerce.entity.Product;
import java.math.BigDecimal;
import java.time.LocalDateTime;

public class ProductResponse {
    private Long id, categoryId, storeId; private String name, description, sku, categoryName, storeName, imageUrl;
    private BigDecimal price; private Integer stock, reviewCount; private Double rating; private LocalDateTime createdAt;

    public Long getId() { return id; } public String getName() { return name; } public String getDescription() { return description; }
    public String getSku() { return sku; } public BigDecimal getPrice() { return price; } public Integer getStock() { return stock; }
    public String getCategoryName() { return categoryName; } public Long getCategoryId() { return categoryId; }
    public String getStoreName() { return storeName; } public Long getStoreId() { return storeId; }
    public String getImageUrl() { return imageUrl; } public Double getRating() { return rating; }
    public Integer getReviewCount() { return reviewCount; } public LocalDateTime getCreatedAt() { return createdAt; }

    public static ProductResponse fromEntity(Product p) {
        ProductResponse r = new ProductResponse();
        r.id=p.getId(); r.name=p.getName(); r.description=p.getDescription(); r.sku=p.getSku();
        r.price=p.getPrice(); r.stock=p.getStock(); r.imageUrl=p.getImageUrl(); r.rating=p.getRating();
        r.reviewCount=p.getReviewCount(); r.createdAt=p.getCreatedAt();
        if (p.getCategory()!=null) { r.categoryName=p.getCategory().getName(); r.categoryId=p.getCategory().getId(); }
        if (p.getStore()!=null) { r.storeName=p.getStore().getName(); r.storeId=p.getStore().getId(); }
        return r;
    }
}

package com.datapulse.ecommerce.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "products", indexes = {
    @Index(name = "idx_product_sku", columnList = "sku"),
    @Index(name = "idx_product_category", columnList = "category_id"),
    @Index(name = "idx_product_store", columnList = "store_id")
})
public class Product {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(nullable = false) private String name;
    @Column(columnDefinition = "TEXT") private String description;
    @Column(nullable = false, unique = true) private String sku;
    @Column(nullable = false, precision = 10, scale = 2) private BigDecimal price;
    @Column(nullable = false) private Integer stock;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "category_id") private Category category;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "store_id") private Store store;
    private String imageUrl;
    @Column(columnDefinition = "DOUBLE") private Double rating;
    private Integer reviewCount;
    @Column(nullable = false, updatable = false) private LocalDateTime createdAt;
    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL) @JsonIgnore
    private List<Review> reviews = new ArrayList<>();

    public Product() {}
    @PrePersist protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        if (this.stock == null) this.stock = 0;
        if (this.reviewCount == null) this.reviewCount = 0;
        if (this.rating == null) this.rating = 0.0;
    }

    public Long getId() { return id; } public void setId(Long id) { this.id = id; }
    public String getName() { return name; } public void setName(String v) { this.name = v; }
    public String getDescription() { return description; } public void setDescription(String v) { this.description = v; }
    public String getSku() { return sku; } public void setSku(String v) { this.sku = v; }
    public BigDecimal getPrice() { return price; } public void setPrice(BigDecimal v) { this.price = v; }
    public Integer getStock() { return stock; } public void setStock(Integer v) { this.stock = v; }
    public Category getCategory() { return category; } public void setCategory(Category v) { this.category = v; }
    public Store getStore() { return store; } public void setStore(Store v) { this.store = v; }
    public String getImageUrl() { return imageUrl; } public void setImageUrl(String v) { this.imageUrl = v; }
    public Double getRating() { return rating; } public void setRating(Double v) { this.rating = v; }
    public Integer getReviewCount() { return reviewCount; } public void setReviewCount(Integer v) { this.reviewCount = v; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public List<Review> getReviews() { return reviews; }

    public static ProductBuilder builder() { return new ProductBuilder(); }
    public static class ProductBuilder {
        private String name, description, sku, imageUrl; private BigDecimal price;
        private Integer stock; private Category category; private Store store;
        private Double rating; private Integer reviewCount;
        public ProductBuilder name(String v) { this.name = v; return this; }
        public ProductBuilder description(String v) { this.description = v; return this; }
        public ProductBuilder sku(String v) { this.sku = v; return this; }
        public ProductBuilder price(BigDecimal v) { this.price = v; return this; }
        public ProductBuilder stock(Integer v) { this.stock = v; return this; }
        public ProductBuilder category(Category v) { this.category = v; return this; }
        public ProductBuilder store(Store v) { this.store = v; return this; }
        public ProductBuilder imageUrl(String v) { this.imageUrl = v; return this; }
        public ProductBuilder rating(Double v) { this.rating = v; return this; }
        public ProductBuilder reviewCount(Integer v) { this.reviewCount = v; return this; }
        public Product build() {
            Product p = new Product(); p.name=name; p.description=description; p.sku=sku; p.price=price;
            p.stock=stock; p.category=category; p.store=store; p.imageUrl=imageUrl; p.rating=rating; p.reviewCount=reviewCount;
            return p;
        }
    }
}

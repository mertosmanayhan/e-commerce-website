package com.datapulse.ecommerce.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity @Table(name = "reviews", indexes = {
    @Index(name = "idx_review_product", columnList = "product_id"),
    @Index(name = "idx_review_user", columnList = "user_id")
})
public class Review {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "user_id", nullable = false) private User user;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "product_id", nullable = false) @JsonIgnore private Product product;
    @Column(nullable = false) private Integer starRating;
    @Column(columnDefinition = "TEXT") private String reviewText;
    @Column(columnDefinition = "TEXT") private String corporateResponse;
    private Integer helpfulVotes; private Integer totalVotes;
    @Column(nullable = false, updatable = false) private LocalDateTime createdAt;
    // Kullanıcılar arası yanıt — parent yorumun ID'si (null ise ana yorum)
    @Column(name = "parent_id") private Long parentId;

    public Review() {}
    @PrePersist protected void onCreate() { this.createdAt = LocalDateTime.now(); if(helpfulVotes==null) helpfulVotes=0; if(totalVotes==null) totalVotes=0; }

    public Long getId() { return id; } public void setId(Long id) { this.id = id; }
    public User getUser() { return user; } public void setUser(User v) { this.user = v; }
    public Product getProduct() { return product; } public void setProduct(Product v) { this.product = v; }
    public Integer getStarRating() { return starRating; } public void setStarRating(Integer v) { this.starRating = v; }
    public String getReviewText() { return reviewText; } public void setReviewText(String v) { this.reviewText = v; }
    public Integer getHelpfulVotes() { return helpfulVotes; } public void setHelpfulVotes(Integer v) { this.helpfulVotes = v; }
    public Integer getTotalVotes() { return totalVotes; } public void setTotalVotes(Integer v) { this.totalVotes = v; }
    public String getCorporateResponse() { return corporateResponse; } public void setCorporateResponse(String v) { this.corporateResponse = v; }
    public Long getParentId() { return parentId; } public void setParentId(Long v) { this.parentId = v; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    public static ReviewBuilder builder() { return new ReviewBuilder(); }
    public static class ReviewBuilder {
        private User user; private Product product; private Integer starRating, helpfulVotes, totalVotes; private String reviewText;
        public ReviewBuilder user(User v) { this.user = v; return this; }
        public ReviewBuilder product(Product v) { this.product = v; return this; }
        public ReviewBuilder starRating(Integer v) { this.starRating = v; return this; }
        public ReviewBuilder reviewText(String v) { this.reviewText = v; return this; }
        public ReviewBuilder helpfulVotes(Integer v) { this.helpfulVotes = v; return this; }
        public ReviewBuilder totalVotes(Integer v) { this.totalVotes = v; return this; }
        public Review build() { Review r = new Review(); r.user=user; r.product=product; r.starRating=starRating; r.reviewText=reviewText; r.helpfulVotes=helpfulVotes; r.totalVotes=totalVotes; return r; }
    }
}

package com.datapulse.ecommerce.dto.request;
public class ReviewRequest {
    private Long productId; private Integer starRating; private String reviewText;
    public Long getProductId() { return productId; } public void setProductId(Long v) { this.productId = v; }
    public Integer getStarRating() { return starRating; } public void setStarRating(Integer v) { this.starRating = v; }
    public String getReviewText() { return reviewText; } public void setReviewText(String v) { this.reviewText = v; }
}

package com.datapulse.ecommerce.dto.request;
public class ReviewRequest {
    private Long productId;
    private Integer starRating;
    private String reviewText;
    private Long parentId; // null ise ana yorum, dolu ise yanıt

    public Long getProductId() { return productId; } public void setProductId(Long v) { this.productId = v; }
    public Integer getStarRating() { return starRating; } public void setStarRating(Integer v) { this.starRating = v; }
    public String getReviewText() { return reviewText; } public void setReviewText(String v) { this.reviewText = v; }
    public Long getParentId() { return parentId; } public void setParentId(Long v) { this.parentId = v; }
}

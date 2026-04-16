package com.datapulse.ecommerce.dto.response;

import com.datapulse.ecommerce.entity.Review;
import java.time.LocalDateTime;
import java.util.List;

public class ReviewResponse {
    private Long id;
    private Long productId;
    private String productName;
    private UserInfo user;
    private Integer starRating;
    private String reviewText;
    private String corporateResponse;
    private Integer helpfulVotes;
    private Integer totalVotes;
    private LocalDateTime createdAt;
    private Long parentId;
    private List<ReviewResponse> replies;

    public static class UserInfo {
        private Long id;
        private String fullName;
        public UserInfo(Long id, String fullName) { this.id = id; this.fullName = fullName; }
        public Long getId() { return id; }
        public String getFullName() { return fullName; }
    }

    public static ReviewResponse fromEntity(Review r) {
        ReviewResponse res = new ReviewResponse();
        res.id = r.getId();
        if (r.getProduct() != null) {
            res.productId = r.getProduct().getId();
            res.productName = r.getProduct().getName();
        }
        if (r.getUser() != null) {
            res.user = new UserInfo(r.getUser().getId(), r.getUser().getFullName());
        }
        res.starRating = r.getStarRating();
        res.reviewText = r.getReviewText();
        res.corporateResponse = r.getCorporateResponse();
        res.helpfulVotes = r.getHelpfulVotes() != null ? r.getHelpfulVotes() : 0;
        res.totalVotes = r.getTotalVotes() != null ? r.getTotalVotes() : 0;
        res.createdAt = r.getCreatedAt();
        res.parentId = r.getParentId();
        return res;
    }

    public Long getId() { return id; }
    public Long getProductId() { return productId; }
    public String getProductName() { return productName; }
    public UserInfo getUser() { return user; }
    public Integer getStarRating() { return starRating; }
    public String getReviewText() { return reviewText; }
    public String getCorporateResponse() { return corporateResponse; }
    public Integer getHelpfulVotes() { return helpfulVotes; }
    public Integer getTotalVotes() { return totalVotes; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public Long getParentId() { return parentId; }
    public List<ReviewResponse> getReplies() { return replies; }
    public void setReplies(List<ReviewResponse> v) { this.replies = v; }
}

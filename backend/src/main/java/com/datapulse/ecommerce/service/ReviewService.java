package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.ReviewRequest;
import com.datapulse.ecommerce.dto.response.ReviewResponse;
import com.datapulse.ecommerce.entity.Product;
import com.datapulse.ecommerce.entity.Review;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.ProductRepository;
import com.datapulse.ecommerce.repository.ReviewRepository;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class ReviewService {
    private final ReviewRepository reviewRepository;
    private final ProductRepository productRepository;
    private final UserRepository userRepository;

    public ReviewService(ReviewRepository rr, ProductRepository pr, UserRepository ur) {
        this.reviewRepository = rr; this.productRepository = pr; this.userRepository = ur;
    }

    @Transactional(readOnly=true)
    public List<ReviewResponse> getAllReviews() {
        return reviewRepository.findAll().stream().map(ReviewResponse::fromEntity).toList();
    }

    @Transactional(readOnly=true)
    public List<ReviewResponse> getReviewsByStoreOwner(Long ownerId) {
        return reviewRepository.findByStoreOwnerId(ownerId).stream().map(ReviewResponse::fromEntity).toList();
    }

    @Transactional(readOnly=true)
    public List<ReviewResponse> getReviewsByProduct(Long productId) {
        // Sadece ana yorumları getir (parentId == null), yanıtlar replies olarak eklenir
        List<Review> allReviews = reviewRepository.findByProductId(productId);
        List<Review> roots = allReviews.stream().filter(r -> r.getParentId() == null).toList();
        return roots.stream().map(r -> {
            ReviewResponse res = ReviewResponse.fromEntity(r);
            List<ReviewResponse> replies = allReviews.stream()
                .filter(c -> r.getId().equals(c.getParentId()))
                .map(ReviewResponse::fromEntity)
                .toList();
            res.setReplies(replies);
            return res;
        }).toList();
    }

    @Transactional
    public ReviewResponse createReview(ReviewRequest req) {
        UserPrincipal principal = (UserPrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        User user = userRepository.findById(principal.getId()).orElseThrow();

        // parentId varsa yanıt yorumu — productId parent'tan al
        final Long productId;
        if (req.getProductId() == null && req.getParentId() != null) {
            Review parent = reviewRepository.findById(req.getParentId())
                    .orElseThrow(() -> new ResourceNotFoundException("Review","id",req.getParentId()));
            productId = parent.getProduct().getId();
        } else {
            productId = req.getProductId();
        }
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new ResourceNotFoundException("Product","id",productId));

        Review review = Review.builder().user(user).product(product)
                .starRating(req.getStarRating() != null ? req.getStarRating() : 0)
                .reviewText(req.getReviewText()).build();
        review.setParentId(req.getParentId());
        review = reviewRepository.save(review);
        // Sadece ana yorumlar ürün puanını etkilesin
        if (req.getParentId() == null) updateProductRating(product);
        return ReviewResponse.fromEntity(review);
    }

    @Transactional
    public ReviewResponse respondToReview(Long id, String response) {
        Review review = reviewRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Review","id",id));
        review.setCorporateResponse(response);
        return ReviewResponse.fromEntity(reviewRepository.save(review));
    }

    @Transactional
    public ReviewResponse voteHelpful(Long id, boolean helpful) {
        Review review = reviewRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Review","id",id));
        review.setTotalVotes((review.getTotalVotes() != null ? review.getTotalVotes() : 0) + 1);
        if (helpful) review.setHelpfulVotes((review.getHelpfulVotes() != null ? review.getHelpfulVotes() : 0) + 1);
        return ReviewResponse.fromEntity(reviewRepository.save(review));
    }

    @Transactional
    public void deleteReview(Long id) {
        Review review = reviewRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Review","id",id));
        Long pid = review.getProduct().getId();
        reviewRepository.delete(review);
        Product product = productRepository.findById(pid).orElseThrow();
        updateProductRating(product);
    }

    private void updateProductRating(Product product) {
        Double avg = reviewRepository.getAverageRatingByProductId(product.getId());
        Integer cnt = reviewRepository.countByProductId(product.getId());
        product.setRating(avg != null ? avg : 0.0);
        product.setReviewCount(cnt != null ? cnt : 0);
        productRepository.save(product);
    }
}

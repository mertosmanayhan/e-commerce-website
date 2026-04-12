package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.ReviewRequest;
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
    private final ReviewRepository reviewRepository; private final ProductRepository productRepository; private final UserRepository userRepository;
    public ReviewService(ReviewRepository rr, ProductRepository pr, UserRepository ur) { this.reviewRepository=rr; this.productRepository=pr; this.userRepository=ur; }

    public List<Review> getAllReviews() { return reviewRepository.findAll(); }
    public List<Review> getReviewsByProduct(Long productId) { return reviewRepository.findByProductId(productId); }

    @Transactional public Review createReview(ReviewRequest req) {
        UserPrincipal principal = (UserPrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        User user = userRepository.findById(principal.getId()).orElseThrow();
        Product product = productRepository.findById(req.getProductId()).orElseThrow(() -> new ResourceNotFoundException("Product","id",req.getProductId()));
        Review review = Review.builder().user(user).product(product).starRating(req.getStarRating()).reviewText(req.getReviewText()).build();
        review = reviewRepository.save(review);
        Double avg = reviewRepository.getAverageRatingByProductId(product.getId());
        Integer cnt = reviewRepository.countByProductId(product.getId());
        product.setRating(avg!=null?avg:0.0); product.setReviewCount(cnt!=null?cnt:0); productRepository.save(product);
        return review;
    }

    @Transactional public Review respondToReview(Long id, String response) {
        Review review = reviewRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Review","id",id));
        review.setCorporateResponse(response);
        return reviewRepository.save(review);
    }

    @Transactional public void deleteReview(Long id) {
        Review review = reviewRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Review","id",id));
        Long pid = review.getProduct().getId(); reviewRepository.delete(review);
        Product product = productRepository.findById(pid).orElseThrow();
        Double avg = reviewRepository.getAverageRatingByProductId(pid);
        Integer cnt = reviewRepository.countByProductId(pid);
        product.setRating(avg!=null?avg:0.0); product.setReviewCount(cnt!=null?cnt:0); productRepository.save(product);
    }
}

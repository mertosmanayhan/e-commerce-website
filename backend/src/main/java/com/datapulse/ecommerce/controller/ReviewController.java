package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.request.ReviewRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.ReviewResponse;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.ReviewService;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController @RequestMapping("/api/reviews") @Tag(name="Reviews")
public class ReviewController {
    private final ReviewService reviewService;
    public ReviewController(ReviewService rs) { this.reviewService = rs; }

    @GetMapping
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<ApiResponse<List<ReviewResponse>>> all(@AuthenticationPrincipal UserPrincipal principal) {
        List<ReviewResponse> result;
        if ("ADMIN".equals(principal.getRole())) {
            result = reviewService.getAllReviews();
        } else if ("CORPORATE".equals(principal.getRole())) {
            result = reviewService.getReviewsByStoreOwner(principal.getId());
        } else {
            result = reviewService.getAllReviews();
        }
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @GetMapping("/product/{productId}")
    public ResponseEntity<ApiResponse<List<ReviewResponse>>> byProduct(@PathVariable Long productId) {
        return ResponseEntity.ok(ApiResponse.success(reviewService.getReviewsByProduct(productId)));
    }

    // Hem INDIVIDUAL hem ADMIN hem CORPORATE yorum yazabilsin
    @PostMapping
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<ApiResponse<ReviewResponse>> create(@Valid @RequestBody ReviewRequest req) {
        return ResponseEntity.ok(ApiResponse.success("Submitted", reviewService.createReview(req)));
    }

    @PatchMapping("/{id}/respond")
    @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')")
    public ResponseEntity<ApiResponse<ReviewResponse>> respond(@PathVariable Long id, @RequestBody Map<String,String> body) {
        return ResponseEntity.ok(ApiResponse.success("Response saved", reviewService.respondToReview(id, body.get("response"))));
    }

    @PostMapping("/{id}/vote")
    @PreAuthorize("isAuthenticated()")
    public ResponseEntity<ApiResponse<ReviewResponse>> vote(@PathVariable Long id, @RequestBody Map<String,Object> body) {
        boolean helpful = Boolean.TRUE.equals(body.get("helpful"));
        return ResponseEntity.ok(ApiResponse.success("Vote recorded", reviewService.voteHelpful(id, helpful)));
    }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) {
        reviewService.deleteReview(id);
        return ResponseEntity.ok(ApiResponse.success("Deleted", null));
    }
}

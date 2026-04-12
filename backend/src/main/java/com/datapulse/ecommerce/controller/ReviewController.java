package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.request.ReviewRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.entity.Review;
import com.datapulse.ecommerce.service.ReviewService;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController @RequestMapping("/api/reviews") @Tag(name="Reviews")
public class ReviewController {
    private final ReviewService reviewService;
    public ReviewController(ReviewService rs) { this.reviewService = rs; }
    @GetMapping public ResponseEntity<ApiResponse<List<Review>>> all() { return ResponseEntity.ok(ApiResponse.success(reviewService.getAllReviews())); }
    @GetMapping("/product/{productId}") public ResponseEntity<ApiResponse<List<Review>>> byProduct(@PathVariable Long productId) { return ResponseEntity.ok(ApiResponse.success(reviewService.getReviewsByProduct(productId))); }
    @PostMapping @PreAuthorize("hasRole('INDIVIDUAL')") public ResponseEntity<ApiResponse<Review>> create(@Valid @RequestBody ReviewRequest req) { return ResponseEntity.ok(ApiResponse.success("Submitted",reviewService.createReview(req))); }
    @PatchMapping("/{id}/respond") @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')") public ResponseEntity<ApiResponse<Review>> respond(@PathVariable Long id, @RequestBody java.util.Map<String,String> body) { return ResponseEntity.ok(ApiResponse.success("Response saved", reviewService.respondToReview(id, body.get("response")))); }
    @DeleteMapping("/{id}") @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')") public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) { reviewService.deleteReview(id); return ResponseEntity.ok(ApiResponse.success("Deleted",null)); }
}

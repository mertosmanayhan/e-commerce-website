package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.ProductResponse;
import com.datapulse.ecommerce.service.WishlistService;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController @RequestMapping("/api/wishlist") @Tag(name="Wishlist") @PreAuthorize("hasAnyRole('INDIVIDUAL', 'CORPORATE', 'ADMIN')")
public class WishlistController {
    private final WishlistService ws;
    public WishlistController(WishlistService ws) { this.ws = ws; }

    @GetMapping public ResponseEntity<ApiResponse<List<ProductResponse>>> get() { return ResponseEntity.ok(ApiResponse.success(ws.getWishlist())); }
    @PostMapping public ResponseEntity<ApiResponse<Void>> add(@RequestBody Map<String,Long> body) {
        ws.addToWishlist(Long.valueOf(body.get("productId").toString())); return ResponseEntity.ok(ApiResponse.success("Added", null));
    }
    @DeleteMapping("/{productId}") public ResponseEntity<ApiResponse<Void>> remove(@PathVariable Long productId) {
        ws.removeFromWishlist(productId); return ResponseEntity.ok(ApiResponse.success("Removed", null));
    }
}

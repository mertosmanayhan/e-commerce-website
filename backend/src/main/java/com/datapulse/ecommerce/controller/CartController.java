package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.CartItemResponse;
import com.datapulse.ecommerce.service.CartService;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController @RequestMapping("/api/cart") @Tag(name="Cart") @PreAuthorize("hasAnyRole('INDIVIDUAL', 'CORPORATE', 'ADMIN')")
public class CartController {
    private final CartService cartService;
    public CartController(CartService cs) { this.cartService = cs; }

    @GetMapping public ResponseEntity<ApiResponse<List<CartItemResponse>>> getCart() { return ResponseEntity.ok(ApiResponse.success(cartService.getCart())); }
    @PostMapping public ResponseEntity<ApiResponse<CartItemResponse>> add(@RequestBody Map<String,Integer> body) {
        return ResponseEntity.ok(ApiResponse.success(cartService.addToCart(Long.valueOf(body.get("productId")), body.get("quantity"))));
    }
    @PatchMapping("/{itemId}") public ResponseEntity<ApiResponse<CartItemResponse>> update(@PathVariable Long itemId, @RequestBody Map<String,Integer> body) {
        return ResponseEntity.ok(ApiResponse.success(cartService.updateQuantity(itemId, body.get("quantity"))));
    }
    @DeleteMapping("/{itemId}") public ResponseEntity<ApiResponse<Void>> remove(@PathVariable Long itemId) {
        cartService.removeFromCart(itemId); return ResponseEntity.ok(ApiResponse.success("Removed", null));
    }
    @DeleteMapping public ResponseEntity<ApiResponse<Void>> clear() {
        cartService.clearCart(); return ResponseEntity.ok(ApiResponse.success("Cart cleared", null));
    }
}

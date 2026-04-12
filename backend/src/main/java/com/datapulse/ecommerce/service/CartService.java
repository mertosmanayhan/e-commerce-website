package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.response.CartItemResponse;
import com.datapulse.ecommerce.entity.CartItem;
import com.datapulse.ecommerce.entity.Product;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.repository.CartItemRepository;
import com.datapulse.ecommerce.repository.ProductRepository;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class CartService {
    private final CartItemRepository cartItemRepository; private final ProductRepository productRepository; private final UserRepository userRepository;
    public CartService(CartItemRepository cir, ProductRepository pr, UserRepository ur) { this.cartItemRepository=cir; this.productRepository=pr; this.userRepository=ur; }

    private User currentUser() {
        UserPrincipal principal = (UserPrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        return userRepository.findById(principal.getId()).orElseThrow();
    }

    private CartItemResponse mapToResponse(CartItem c) {
        CartItemResponse r = new CartItemResponse();
        r.setId(c.getId()); r.setProductId(c.getProduct().getId()); r.setProductName(c.getProduct().getName());
        r.setProductSku(c.getProduct().getSku()); r.setImageUrl(c.getProduct().getImageUrl());
        r.setPrice(c.getProduct().getPrice()); r.setQuantity(c.getQuantity()); return r;
    }

    public List<CartItemResponse> getCart() {
        return cartItemRepository.findByUserId(currentUser().getId()).stream().map(this::mapToResponse).toList();
    }

    @Transactional public CartItemResponse addToCart(Long productId, Integer quantity) {
        User user = currentUser();
        CartItem existing = cartItemRepository.findByUserIdAndProductId(user.getId(), productId);
        if (existing != null) {
            existing.setQuantity(existing.getQuantity() + quantity);
            return mapToResponse(cartItemRepository.save(existing));
        }
        Product p = productRepository.findById(productId).orElseThrow();
        CartItem item = new CartItem(user, p, quantity);
        return mapToResponse(cartItemRepository.save(item));
    }

    @Transactional public CartItemResponse updateQuantity(Long itemId, Integer quantity) {
        CartItem item = cartItemRepository.findById(itemId).orElseThrow();
        if(!item.getUser().getId().equals(currentUser().getId())) throw new IllegalArgumentException("Unauthorized");
        if(quantity <= 0) { cartItemRepository.delete(item); return null; }
        item.setQuantity(quantity); return mapToResponse(cartItemRepository.save(item));
    }

    @Transactional public void removeFromCart(Long itemId) {
        CartItem item = cartItemRepository.findById(itemId).orElseThrow();
        if(item.getUser().getId().equals(currentUser().getId())) cartItemRepository.delete(item);
    }

    @Transactional public void clearCart() { cartItemRepository.deleteByUserId(currentUser().getId()); }
}

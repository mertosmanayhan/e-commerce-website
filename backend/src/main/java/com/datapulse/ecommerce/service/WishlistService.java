package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.response.ProductResponse;
import com.datapulse.ecommerce.entity.Product;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.entity.WishlistItem;
import com.datapulse.ecommerce.repository.ProductRepository;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.repository.WishlistItemRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class WishlistService {
    private final WishlistItemRepository wr; private final ProductRepository pr; private final UserRepository ur;
    public WishlistService(WishlistItemRepository wr, ProductRepository pr, UserRepository ur) { this.wr=wr; this.pr=pr; this.ur=ur; }

    private User currentUser() {
        UserPrincipal principal = (UserPrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        return ur.findById(principal.getId()).orElseThrow();
    }

    public List<ProductResponse> getWishlist() {
        return wr.findByUserId(currentUser().getId()).stream().map(w -> ProductResponse.fromEntity(w.getProduct())).toList();
    }

    @Transactional public void addToWishlist(Long productId) {
        User u = currentUser();
        if(wr.findByUserIdAndProductId(u.getId(), productId) == null) {
            Product p = pr.findById(productId).orElseThrow();
            wr.save(new WishlistItem(u, p));
        }
    }

    @Transactional public void removeFromWishlist(Long productId) {
        WishlistItem item = wr.findByUserIdAndProductId(currentUser().getId(), productId);
        if(item != null) wr.delete(item);
    }
}

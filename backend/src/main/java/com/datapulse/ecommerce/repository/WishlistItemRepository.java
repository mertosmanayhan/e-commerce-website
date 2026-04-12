package com.datapulse.ecommerce.repository;
import com.datapulse.ecommerce.entity.WishlistItem;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface WishlistItemRepository extends JpaRepository<WishlistItem, Long> {
    List<WishlistItem> findByUserId(Long userId);
    WishlistItem findByUserIdAndProductId(Long userId, Long productId);
}

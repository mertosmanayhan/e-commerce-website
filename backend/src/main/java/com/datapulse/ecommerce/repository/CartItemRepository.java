package com.datapulse.ecommerce.repository;
import com.datapulse.ecommerce.entity.CartItem;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface CartItemRepository extends JpaRepository<CartItem, Long> {
    List<CartItem> findByUserId(Long userId);
    CartItem findByUserIdAndProductId(Long userId, Long productId);
    void deleteByUserId(Long userId);
}

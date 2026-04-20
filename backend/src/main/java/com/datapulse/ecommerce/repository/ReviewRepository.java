package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.Review;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.List;

public interface ReviewRepository extends JpaRepository<Review, Long> {
    List<Review> findByProductId(Long productId);
    void deleteByProductId(Long productId);
    List<Review> findByUserId(Long userId);
    List<Review> findByParentId(Long parentId);

    // Bir mağaza sahibinin mağazalarına ait ürünlerin yorumları
    @Query("SELECT r FROM Review r WHERE r.product.store.owner.id = :ownerId")
    List<Review> findByStoreOwnerId(@Param("ownerId") Long ownerId);

    @Query("SELECT AVG(r.starRating) FROM Review r WHERE r.product.id = :productId")
    Double getAverageRatingByProductId(@Param("productId") Long productId);

    @Query("SELECT COUNT(r) FROM Review r WHERE r.product.id = :productId")
    Integer countByProductId(@Param("productId") Long productId);
}

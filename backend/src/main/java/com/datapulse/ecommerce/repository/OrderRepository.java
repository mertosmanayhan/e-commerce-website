package com.datapulse.ecommerce.repository;

import com.datapulse.ecommerce.entity.Order;
import com.datapulse.ecommerce.entity.enums.OrderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface OrderRepository extends JpaRepository<Order, Long> {

    Page<Order> findByUserId(Long userId, Pageable pageable);

    @Query("SELECT DISTINCT o FROM Order o JOIN o.items oi JOIN oi.product p WHERE p.store.owner.id = :ownerId")
    Page<Order> findByStoreOwnerId(@Param("ownerId") Long ownerId, Pageable pageable);

    Optional<Order> findByOrderNumber(String orderNumber);

    List<Order> findByStatus(OrderStatus status);

    @Query("SELECT o FROM Order o JOIN o.items oi JOIN oi.product p WHERE p.store.id = :storeId")
    Page<Order> findByStoreId(@Param("storeId") Long storeId, Pageable pageable);

    @Query("SELECT o FROM Order o WHERE o.orderDate BETWEEN :start AND :end")
    List<Order> findByDateRange(@Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(o) FROM Order o WHERE o.status = :status")
    Long countByStatus(@Param("status") OrderStatus status);

    @Query("SELECT COUNT(o) FROM Order o WHERE o.status = :status AND o.orderDate BETWEEN :start AND :end")
    Long countByStatusAndDateRange(@Param("status") OrderStatus status,
                                   @Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(o) FROM Order o WHERE o.orderDate BETWEEN :start AND :end")
    Long countByDateRange(@Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT SUM(o.totalAmount) FROM Order o WHERE o.orderDate BETWEEN :start AND :end")
    BigDecimal sumRevenueByDateRange(@Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    // Item bazlı platform geliri (store geliriyle tutarlı)
    @Query("SELECT SUM(oi.unitPrice * oi.quantity) FROM OrderItem oi WHERE oi.order.orderDate BETWEEN :start AND :end")
    BigDecimal sumItemRevenueByDateRange(@Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    // ── Analytics queries ──────────────────────────────────────────────────

    // Sadece o mağazanın ürünlerinden gelen gelir (sipariş toplamı değil, ürün bazlı)
    @Query("SELECT SUM(oi.unitPrice * oi.quantity) FROM OrderItem oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId AND oi.order.orderDate BETWEEN :start AND :end")
    BigDecimal sumRevenueByStoreAndDateRange(@Param("storeId") Long storeId,
                                             @Param("start") LocalDateTime start,
                                             @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(DISTINCT o.id) FROM Order o JOIN o.items oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId AND o.orderDate BETWEEN :start AND :end")
    Long countOrdersByStoreAndDateRange(@Param("storeId") Long storeId,
                                        @Param("start") LocalDateTime start,
                                        @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(DISTINCT o.id) FROM Order o JOIN o.items oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId AND o.status = :status AND o.orderDate BETWEEN :start AND :end")
    Long countByStoreAndStatusAndDateRange(@Param("storeId") Long storeId, @Param("status") OrderStatus status,
                                           @Param("start") LocalDateTime start, @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(DISTINCT o.id) FROM Order o JOIN o.items oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId AND o.status = :status")
    Long countByStoreAndStatus(@Param("storeId") Long storeId, @Param("status") OrderStatus status);

    @Query("SELECT COUNT(DISTINCT o.user.id) FROM Order o JOIN o.items oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId AND o.orderDate BETWEEN :start AND :end")
    Long countDistinctCustomersByStoreAndDateRange(@Param("storeId") Long storeId,
                                                   @Param("start") LocalDateTime start,
                                                   @Param("end") LocalDateTime end);

    @Query("SELECT COUNT(DISTINCT o.user.id) FROM Order o JOIN o.items oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId")
    Long countDistinctCustomersByStore(@Param("storeId") Long storeId);

    @Query(value = "SELECT DATE(o.order_date) as day, SUM(o.total_amount) as revenue " +
                   "FROM orders o JOIN order_items oi ON o.id = oi.order_id " +
                   "JOIN products p ON oi.product_id = p.id " +
                   "WHERE p.store_id = :storeId AND o.order_date >= :since " +
                   "GROUP BY DATE(o.order_date) ORDER BY day",
           nativeQuery = true)
    List<Object[]> getDailyRevenueByStore(@Param("storeId") Long storeId, @Param("since") LocalDateTime since);

    @Query("SELECT COALESCE(c.name, 'Other'), SUM(oi.unitPrice * oi.quantity) " +
           "FROM OrderItem oi JOIN oi.product p LEFT JOIN p.category c " +
           "WHERE p.store.id = :storeId GROUP BY c.name ORDER BY 2 DESC")
    List<Object[]> getRevenueByCategoryForStore(@Param("storeId") Long storeId);

    @Query("SELECT p.name, SUM(oi.quantity), SUM(oi.unitPrice * oi.quantity) " +
           "FROM OrderItem oi JOIN oi.product p " +
           "WHERE p.store.id = :storeId GROUP BY p.id, p.name ORDER BY 3 DESC")
    List<Object[]> getTopProductsForStore(@Param("storeId") Long storeId, Pageable pageable);

    @Query(value = "SELECT DATE(order_date) as day, SUM(total_amount) as revenue " +
                   "FROM orders WHERE order_date >= :since GROUP BY DATE(order_date) ORDER BY day",
           nativeQuery = true)
    List<Object[]> getDailyRevenue(@Param("since") LocalDateTime since);

    @Query("SELECT COALESCE(c.name, 'Other') as catName, SUM(oi.unitPrice * oi.quantity) as rev " +
           "FROM OrderItem oi JOIN oi.product p LEFT JOIN p.category c " +
           "GROUP BY c.name ORDER BY rev DESC")
    List<Object[]> getRevenueByCategory();

    @Query("SELECT p.name, SUM(oi.quantity) as totalSold, SUM(oi.unitPrice * oi.quantity) as totalRev " +
           "FROM OrderItem oi JOIN oi.product p GROUP BY p.id, p.name ORDER BY totalRev DESC")
    List<Object[]> getTopProducts(Pageable pageable);

    @Query("SELECT SUM(o.totalAmount) FROM Order o WHERE o.user.id = :userId")
    BigDecimal getTotalSpendByUser(@Param("userId") Long userId);

    @Query("SELECT COUNT(o) FROM Order o WHERE o.user.id = :userId")
    Long countOrdersByUser(@Param("userId") Long userId);

    @Query("SELECT COALESCE(c.name, 'Other'), COUNT(oi.id) FROM OrderItem oi " +
           "JOIN oi.product p LEFT JOIN p.category c " +
           "WHERE oi.order.user.id = :userId GROUP BY c.name ORDER BY 2 DESC")
    List<Object[]> getCategoryFrequencyByUser(@Param("userId") Long userId, Pageable pageable);

    @Query(value = "SELECT DATE(o.order_date) as day, SUM(o.total_amount) as revenue " +
                   "FROM orders o WHERE o.user_id = :userId AND o.order_date >= :since " +
                   "GROUP BY DATE(o.order_date) ORDER BY day",
           nativeQuery = true)
    List<Object[]> getUserSpendTrend(@Param("userId") Long userId, @Param("since") LocalDateTime since);

    @Query("SELECT u.fullName, u.email, SUM(o.totalAmount), COUNT(o) " +
           "FROM Order o JOIN o.user u GROUP BY u.id, u.fullName, u.email ORDER BY 3 DESC")
    List<Object[]> getTopSpenders(Pageable pageable);
}

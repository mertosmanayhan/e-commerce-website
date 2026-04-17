package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.response.DashboardResponse;
import com.datapulse.ecommerce.dto.response.DashboardResponse.ChartPoint;
import com.datapulse.ecommerce.dto.response.DashboardResponse.TopProduct;
import com.datapulse.ecommerce.dto.response.IndividualAnalyticsResponse;
import com.datapulse.ecommerce.entity.enums.OrderStatus;
import com.datapulse.ecommerce.repository.*;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Service
public class AnalyticsService {

    private final OrderRepository orderRepository;
    private final UserRepository userRepository;
    private final ProductRepository productRepository;
    private final StoreRepository storeRepository;

    public AnalyticsService(OrderRepository or, UserRepository ur, ProductRepository pr, StoreRepository sr) {
        this.orderRepository = or;
        this.userRepository = ur;
        this.productRepository = pr;
        this.storeRepository = sr;
    }

    // ── Corporate / Admin dashboard ───────────────────────────────────────

    public DashboardResponse getDashboardData() { return getDashboardData(30); }
    public DashboardResponse getDashboardData(int days) {
        LocalDateTime now      = LocalDateTime.now();
        LocalDateTime curStart = now.minusDays(days);
        LocalDateTime prevStart = now.minusDays(days * 2L);

        BigDecimal curRev  = nullSafe(orderRepository.sumItemRevenueByDateRange(curStart, now));
        BigDecimal prevRev = nullSafe(orderRepository.sumItemRevenueByDateRange(prevStart, curStart));

        long curOrders  = nullSafe(orderRepository.countByDateRange(curStart, now));
        long prevOrders = nullSafe(orderRepository.countByDateRange(prevStart, curStart));

        long pending   = nullSafe(orderRepository.countByStatusAndDateRange(OrderStatus.PENDING,   curStart, now));
        long shipped   = nullSafe(orderRepository.countByStatusAndDateRange(OrderStatus.SHIPPED,   curStart, now));
        long delivered = nullSafe(orderRepository.countByStatusAndDateRange(OrderStatus.DELIVERED, curStart, now));
        long cancelled = nullSafe(orderRepository.countByStatusAndDateRange(OrderStatus.CANCELLED, curStart, now));

        double avgRating = productRepository.findAll().stream()
                .filter(p -> p.getRating() != null && p.getRating() > 0)
                .mapToDouble(p -> p.getRating()).average().orElse(0.0);

        return DashboardResponse.builder()
                .totalRevenue(curRev)
                .revenueGrowth(calcGrowth(prevRev, curRev))
                .totalOrders(curOrders)
                .ordersGrowth(calcGrowthL(prevOrders, curOrders))
                .totalCustomers(userRepository.count())
                .customersGrowth("+0%")
                .averageRating(Math.round(avgRating * 10.0) / 10.0)
                .ratingGrowth("+0.0")
                .pendingOrders(pending)
                .shippedOrders(shipped)
                .deliveredOrders(delivered)
                .cancelledOrders(cancelled)
                .salesTrend(buildSalesTrend(now.minusDays(Math.min(days, 90))))
                .categoryBreakdown(buildCategoryBreakdown())
                .topProducts(buildTopProducts())
                .build();
    }

    // ── Corporate dashboard — kendi mağazasının verisi ───────────────────

    public DashboardResponse getStoreDashboardData(Long ownerId) { return getStoreDashboardData(ownerId, 30); }
    public DashboardResponse getStoreDashboardData(Long ownerId, int days) {
        // Sahibin mağazalarını bul (ilk mağaza)
        List<com.datapulse.ecommerce.entity.Store> stores = storeRepository.findByOwnerId(ownerId);
        if (stores.isEmpty()) {
            return DashboardResponse.builder()
                    .totalRevenue(BigDecimal.ZERO).revenueGrowth("0%")
                    .totalOrders(0L).ordersGrowth("0%")
                    .totalCustomers(0L).customersGrowth("0%")
                    .averageRating(0.0).ratingGrowth("+0.0")
                    .pendingOrders(0L).shippedOrders(0L).deliveredOrders(0L).cancelledOrders(0L)
                    .salesTrend(new ArrayList<>()).categoryBreakdown(new ArrayList<>()).topProducts(new ArrayList<>())
                    .build();
        }

        Long storeId = stores.get(0).getId();
        LocalDateTime now      = LocalDateTime.now();
        LocalDateTime curStart = now.minusDays(days);
        LocalDateTime prevStart = now.minusDays(days * 2L);

        BigDecimal curRev  = nullSafe(orderRepository.sumRevenueByStoreAndDateRange(storeId, curStart, now));
        BigDecimal prevRev = nullSafe(orderRepository.sumRevenueByStoreAndDateRange(storeId, prevStart, curStart));

        long curOrders  = nullSafe(orderRepository.countOrdersByStoreAndDateRange(storeId, curStart, now));
        long prevOrders = nullSafe(orderRepository.countOrdersByStoreAndDateRange(storeId, prevStart, curStart));

        long pending   = nullSafe(orderRepository.countByStoreAndStatusAndDateRange(storeId, OrderStatus.PENDING,   curStart, now));
        long shipped   = nullSafe(orderRepository.countByStoreAndStatusAndDateRange(storeId, OrderStatus.SHIPPED,   curStart, now));
        long delivered = nullSafe(orderRepository.countByStoreAndStatusAndDateRange(storeId, OrderStatus.DELIVERED, curStart, now));
        long cancelled = nullSafe(orderRepository.countByStoreAndStatusAndDateRange(storeId, OrderStatus.CANCELLED, curStart, now));

        long customers = nullSafe(orderRepository.countDistinctCustomersByStoreAndDateRange(storeId, curStart, now));

        // Mağazanın ürünlerinin ortalama puanı
        double avgRating = stores.get(0).getProducts().stream()
                .filter(p -> p.getRating() != null && p.getRating() > 0)
                .mapToDouble(p -> p.getRating()).average().orElse(0.0);

        // Store bazlı trend ve kategori
        List<ChartPoint> trend = new ArrayList<>();
        try {
            for (Object[] row : orderRepository.getDailyRevenueByStore(storeId, now.minusDays(14))) {
                trend.add(new ChartPoint(
                        row[0] != null ? row[0].toString() : "N/A",
                        row[1] != null ? ((Number) row[1]).doubleValue() : 0.0));
            }
        } catch (Exception ignored) {}

        List<ChartPoint> catBreakdown = new ArrayList<>();
        try {
            for (Object[] row : orderRepository.getRevenueByCategoryForStore(storeId)) {
                catBreakdown.add(new ChartPoint(
                        row[0] != null ? row[0].toString() : "Other",
                        row[1] != null ? ((Number) row[1]).doubleValue() : 0.0));
            }
        } catch (Exception ignored) {}

        List<TopProduct> topProducts = new ArrayList<>();
        try {
            for (Object[] row : orderRepository.getTopProductsForStore(storeId, PageRequest.of(0, 5))) {
                topProducts.add(new TopProduct(
                        row[0] != null ? row[0].toString() : "Unknown",
                        row[1] != null ? ((Number) row[1]).longValue() : 0L,
                        row[2] != null ? ((Number) row[2]).doubleValue() : 0.0));
            }
        } catch (Exception ignored) {}

        return DashboardResponse.builder()
                .totalRevenue(curRev)
                .revenueGrowth(calcGrowth(prevRev, curRev))
                .totalOrders(curOrders)
                .ordersGrowth(calcGrowthL(prevOrders, curOrders))
                .totalCustomers(customers)
                .customersGrowth("+0%")
                .averageRating(Math.round(avgRating * 10.0) / 10.0)
                .ratingGrowth("+0.0")
                .pendingOrders(pending)
                .shippedOrders(shipped)
                .deliveredOrders(delivered)
                .cancelledOrders(cancelled)
                .salesTrend(trend)
                .categoryBreakdown(catBreakdown)
                .topProducts(topProducts)
                .build();
    }

    // ── Individual analytics ──────────────────────────────────────────────

    public IndividualAnalyticsResponse getIndividualAnalytics(Long userId) { return getIndividualAnalytics(userId, 30); }
    public IndividualAnalyticsResponse getIndividualAnalytics(Long userId, int days) {
        BigDecimal totalSpend  = nullSafe(orderRepository.getTotalSpendByUser(userId));
        Long       totalOrders = nullSafeL(orderRepository.countOrdersByUser(userId));

        BigDecimal avgOrderValue = totalOrders > 0
                ? totalSpend.divide(BigDecimal.valueOf(totalOrders), 2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        // Favorite category
        String favoriteCategory = "N/A";
        List<Object[]> catFreq = orderRepository.getCategoryFrequencyByUser(userId, PageRequest.of(0, 1));
        if (!catFreq.isEmpty() && catFreq.get(0)[0] != null) {
            favoriteCategory = catFreq.get(0)[0].toString();
        }

        // Spend trend
        List<ChartPoint> spendTrend = new ArrayList<>();
        for (Object[] row : orderRepository.getUserSpendTrend(userId, LocalDateTime.now().minusDays(days))) {
            spendTrend.add(new ChartPoint(
                    row[0] != null ? row[0].toString() : "N/A",
                    row[1] != null ? ((Number) row[1]).doubleValue() : 0.0));
        }

        // Category breakdown (top 5)
        List<ChartPoint> catBreakdown = new ArrayList<>();
        for (Object[] row : orderRepository.getCategoryFrequencyByUser(userId, PageRequest.of(0, 5))) {
            catBreakdown.add(new ChartPoint(
                    row[0] != null ? row[0].toString() : "Other",
                    row[1] != null ? ((Number) row[1]).doubleValue() : 0.0));
        }

        IndividualAnalyticsResponse res = new IndividualAnalyticsResponse();
        res.setTotalSpend(totalSpend);
        res.setTotalOrders(totalOrders);
        res.setAvgOrderValue(avgOrderValue);
        res.setFavoriteCategory(favoriteCategory);
        res.setSpendTrend(spendTrend);
        res.setCategoryBreakdown(catBreakdown);
        return res;
    }

    // ── Customer segmentation ─────────────────────────────────────────────

    public java.util.Map<String, Object> getCustomerSegments(Long ownerId, String role) {
        java.util.Map<String, Object> result = new java.util.LinkedHashMap<>();

        // Total customers by role
        long individual = userRepository.countByRole(com.datapulse.ecommerce.entity.enums.Role.INDIVIDUAL);
        long corporate  = userRepository.countByRole(com.datapulse.ecommerce.entity.enums.Role.CORPORATE);

        // Top spenders (top 5 users by total spend)
        List<Object[]> topSpenders = orderRepository.getTopSpenders(PageRequest.of(0, 5));
        List<java.util.Map<String,Object>> spenderList = new ArrayList<>();
        for (Object[] row : topSpenders) {
            java.util.Map<String,Object> m = new java.util.LinkedHashMap<>();
            m.put("name",  row[0] != null ? row[0].toString() : "Unknown");
            m.put("email", row[1] != null ? row[1].toString() : "");
            m.put("total", row[2] != null ? ((Number) row[2]).doubleValue() : 0.0);
            m.put("orders",row[3] != null ? ((Number) row[3]).longValue()  : 0L);
            spenderList.add(m);
        }

        // New customers last 30 days
        long newCustomers = userRepository.countByCreatedAtAfter(LocalDateTime.now().minusDays(30));

        result.put("totalIndividual", individual);
        result.put("totalCorporate",  corporate);
        result.put("newCustomers30d", newCustomers);
        result.put("topSpenders",     spenderList);
        return result;
    }

    // ── Private helpers ───────────────────────────────────────────────────

    private List<ChartPoint> buildSalesTrend(LocalDateTime since) {
        List<ChartPoint> trend = new ArrayList<>();
        try {
            for (Object[] row : orderRepository.getDailyRevenue(since)) {
                trend.add(new ChartPoint(
                        row[0] != null ? row[0].toString() : "N/A",
                        row[1] != null ? ((Number) row[1]).doubleValue() : 0.0));
            }
        } catch (Exception ignored) {}
        return trend;
    }

    private List<ChartPoint> buildCategoryBreakdown() {
        List<ChartPoint> breakdown = new ArrayList<>();
        try {
            for (Object[] row : orderRepository.getRevenueByCategory()) {
                breakdown.add(new ChartPoint(
                        row[0] != null ? row[0].toString() : "Other",
                        row[1] != null ? ((Number) row[1]).doubleValue() : 0.0));
            }
        } catch (Exception ignored) {}
        return breakdown;
    }

    private List<TopProduct> buildTopProducts() {
        List<TopProduct> top = new ArrayList<>();
        try {
            for (Object[] row : orderRepository.getTopProducts(PageRequest.of(0, 5))) {
                top.add(new TopProduct(
                        row[0] != null ? row[0].toString() : "Unknown",
                        row[1] != null ? ((Number) row[1]).longValue() : 0L,
                        row[2] != null ? ((Number) row[2]).doubleValue() : 0.0));
            }
        } catch (Exception ignored) {}
        return top;
    }

    private BigDecimal nullSafe(BigDecimal v) { return v != null ? v : BigDecimal.ZERO; }
    private long nullSafe(Long v)             { return v != null ? v : 0L; }
    private Long nullSafeL(Long v)            { return v != null ? v : 0L; }

    private String calcGrowth(BigDecimal prev, BigDecimal cur) {
        if (prev.compareTo(BigDecimal.ZERO) == 0)
            return cur.compareTo(BigDecimal.ZERO) > 0 ? "+100%" : "0%";
        BigDecimal g = cur.subtract(prev).divide(prev, 4, RoundingMode.HALF_UP).multiply(BigDecimal.valueOf(100));
        return (g.compareTo(BigDecimal.ZERO) >= 0 ? "+" : "") + g.setScale(1, RoundingMode.HALF_UP) + "%";
    }

    private String calcGrowthL(long prev, long cur) {
        if (prev == 0) return cur > 0 ? "+100%" : "0%";
        double g = ((double) (cur - prev) / prev) * 100;
        return (g >= 0 ? "+" : "") + String.format("%.1f", g) + "%";
    }
}

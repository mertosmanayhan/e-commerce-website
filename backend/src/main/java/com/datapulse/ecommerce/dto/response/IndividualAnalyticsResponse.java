package com.datapulse.ecommerce.dto.response;

import java.math.BigDecimal;
import java.util.List;

public class IndividualAnalyticsResponse {

    private BigDecimal totalSpend;
    private Long totalOrders;
    private BigDecimal avgOrderValue;
    private String favoriteCategory;
    private List<DashboardResponse.ChartPoint> spendTrend;
    private List<DashboardResponse.ChartPoint> categoryBreakdown;

    public BigDecimal getTotalSpend() { return totalSpend; }
    public void setTotalSpend(BigDecimal v) { this.totalSpend = v; }
    public Long getTotalOrders() { return totalOrders; }
    public void setTotalOrders(Long v) { this.totalOrders = v; }
    public BigDecimal getAvgOrderValue() { return avgOrderValue; }
    public void setAvgOrderValue(BigDecimal v) { this.avgOrderValue = v; }
    public String getFavoriteCategory() { return favoriteCategory; }
    public void setFavoriteCategory(String v) { this.favoriteCategory = v; }
    public List<DashboardResponse.ChartPoint> getSpendTrend() { return spendTrend; }
    public void setSpendTrend(List<DashboardResponse.ChartPoint> v) { this.spendTrend = v; }
    public List<DashboardResponse.ChartPoint> getCategoryBreakdown() { return categoryBreakdown; }
    public void setCategoryBreakdown(List<DashboardResponse.ChartPoint> v) { this.categoryBreakdown = v; }
}

package com.datapulse.ecommerce.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity @Table(name = "customer_profiles")
public class CustomerProfile {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @OneToOne(fetch = FetchType.LAZY) @JoinColumn(name = "user_id", nullable = false, unique = true) private User user;
    private String membershipType;
    @Column(precision = 12, scale = 2) private BigDecimal totalSpend;
    private Integer itemsPurchased;
    @Column(columnDefinition = "DOUBLE") private Double avgRating;
    private Boolean discountApplied; private String satisfactionLevel;

    public CustomerProfile() {}
    public Long getId() { return id; } public User getUser() { return user; } public void setUser(User v) { this.user = v; }
    public String getMembershipType() { return membershipType; } public void setMembershipType(String v) { this.membershipType = v; }
    public BigDecimal getTotalSpend() { return totalSpend; } public void setTotalSpend(BigDecimal v) { this.totalSpend = v; }
    public Integer getItemsPurchased() { return itemsPurchased; } public void setItemsPurchased(Integer v) { this.itemsPurchased = v; }
    public Double getAvgRating() { return avgRating; } public void setAvgRating(Double v) { this.avgRating = v; }
    public Boolean getDiscountApplied() { return discountApplied; } public void setDiscountApplied(Boolean v) { this.discountApplied = v; }
    public String getSatisfactionLevel() { return satisfactionLevel; } public void setSatisfactionLevel(String v) { this.satisfactionLevel = v; }

    public static CPBuilder builder() { return new CPBuilder(); }
    public static class CPBuilder {
        private User user; private String membershipType, satisfactionLevel; private BigDecimal totalSpend;
        private Integer itemsPurchased; private Double avgRating; private Boolean discountApplied;
        public CPBuilder user(User v) { this.user = v; return this; }
        public CPBuilder membershipType(String v) { this.membershipType = v; return this; }
        public CPBuilder totalSpend(BigDecimal v) { this.totalSpend = v; return this; }
        public CPBuilder itemsPurchased(Integer v) { this.itemsPurchased = v; return this; }
        public CPBuilder avgRating(Double v) { this.avgRating = v; return this; }
        public CPBuilder discountApplied(Boolean v) { this.discountApplied = v; return this; }
        public CPBuilder satisfactionLevel(String v) { this.satisfactionLevel = v; return this; }
        public CustomerProfile build() { CustomerProfile c = new CustomerProfile(); c.user=user; c.membershipType=membershipType; c.totalSpend=totalSpend; c.itemsPurchased=itemsPurchased; c.avgRating=avgRating; c.discountApplied=discountApplied; c.satisfactionLevel=satisfactionLevel; return c; }
    }
}

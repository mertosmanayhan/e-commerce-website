package com.datapulse.ecommerce.entity;
import jakarta.persistence.*;

@Entity @Table(name = "wishlist_items")
public class WishlistItem {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    public WishlistItem() {}
    public WishlistItem(User u, Product p) { this.user=u; this.product=p; }

    public Long getId() { return id; } public void setId(Long v) { this.id = v; }
    public User getUser() { return user; } public void setUser(User v) { this.user = v; }
    public Product getProduct() { return product; } public void setProduct(Product v) { this.product = v; }
}

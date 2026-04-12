package com.datapulse.ecommerce.entity;
import jakarta.persistence.*;

@Entity @Table(name = "cart_items")
public class CartItem {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "product_id", nullable = false)
    private Product product;

    @Column(nullable = false)
    private Integer quantity;

    public CartItem() {}
    public CartItem(User u, Product p, Integer q) { this.user=u; this.product=p; this.quantity=q; }

    public Long getId() { return id; } public void setId(Long v) { this.id = v; }
    public User getUser() { return user; } public void setUser(User v) { this.user = v; }
    public Product getProduct() { return product; } public void setProduct(Product v) { this.product = v; }
    public Integer getQuantity() { return quantity; } public void setQuantity(Integer v) { this.quantity = v; }
}

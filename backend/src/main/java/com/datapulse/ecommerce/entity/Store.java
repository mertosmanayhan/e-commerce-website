package com.datapulse.ecommerce.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "stores")
public class Store {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @Column(nullable = false) private String name;
    @Column(columnDefinition = "TEXT") private String description;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "owner_id", nullable = false)
    private User owner;
    @Column(nullable = false) private Boolean isOpen = true;
    @OneToMany(mappedBy = "store", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Product> products = new ArrayList<>();
    @Column(nullable = false, updatable = false) private LocalDateTime createdAt;

    public Store() {}
    @PrePersist protected void onCreate() { this.createdAt = LocalDateTime.now(); if (this.isOpen == null) this.isOpen = true; }

    public Long getId() { return id; } public void setId(Long id) { this.id = id; }
    public String getName() { return name; } public void setName(String name) { this.name = name; }
    public String getDescription() { return description; } public void setDescription(String d) { this.description = d; }
    public User getOwner() { return owner; } public void setOwner(User owner) { this.owner = owner; }
    public Boolean getIsOpen() { return isOpen; } public void setIsOpen(Boolean v) { this.isOpen = v; }
    public List<Product> getProducts() { return products; } public void setProducts(List<Product> p) { this.products = p; }
    public LocalDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(LocalDateTime c) { this.createdAt = c; }

    public static StoreBuilder builder() { return new StoreBuilder(); }
    public static class StoreBuilder {
        private String name, description; private User owner; private Boolean isOpen = true;
        public StoreBuilder name(String v) { this.name = v; return this; }
        public StoreBuilder description(String v) { this.description = v; return this; }
        public StoreBuilder owner(User v) { this.owner = v; return this; }
        public StoreBuilder isOpen(Boolean v) { this.isOpen = v; return this; }
        public Store build() { Store s = new Store(); s.name=name; s.description=description; s.owner=owner; s.isOpen=isOpen; return s; }
    }
}

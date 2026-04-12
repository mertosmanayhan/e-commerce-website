package com.datapulse.ecommerce.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "categories")
public class Category {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(nullable = false, unique = true) private String name;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "parent_id") @JsonIgnore
    private Category parentCategory;
    @OneToMany(mappedBy = "parentCategory", cascade = CascadeType.ALL) @JsonIgnore
    private List<Category> subCategories = new ArrayList<>();
    @OneToMany(mappedBy = "category") @JsonIgnore
    private List<Product> products = new ArrayList<>();

    public Category() {}
    public Long getId() { return id; } public void setId(Long id) { this.id = id; }
    public String getName() { return name; } public void setName(String name) { this.name = name; }
    public Category getParentCategory() { return parentCategory; } public void setParentCategory(Category p) { this.parentCategory = p; }
    public List<Category> getSubCategories() { return subCategories; }
    public List<Product> getProducts() { return products; }

    public static CategoryBuilder builder() { return new CategoryBuilder(); }
    public static class CategoryBuilder {
        private String name;
        public CategoryBuilder name(String v) { this.name = v; return this; }
        public Category build() { Category c = new Category(); c.name = name; return c; }
    }
}

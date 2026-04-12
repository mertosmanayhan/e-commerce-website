package com.datapulse.ecommerce.dto.response;

import com.datapulse.ecommerce.entity.Store;
import java.time.LocalDateTime;

public class StoreResponse {
    private Long id;
    private String name;
    private String description;
    private String ownerName;
    private String ownerEmail;
    private String address;
    private String email;
    private boolean open;
    private int productCount;
    private LocalDateTime createdAt;

    public StoreResponse() {}

    public static StoreResponse fromEntity(Store s) {
        StoreResponse r = new StoreResponse();
        r.id = s.getId();
        r.name = s.getName();
        r.description = s.getDescription();
        if (s.getOwner() != null) {
            r.ownerName  = s.getOwner().getFullName();
            r.ownerEmail = s.getOwner().getEmail();
        }
        r.open = Boolean.TRUE.equals(s.getIsOpen());
        r.productCount = s.getProducts() != null ? s.getProducts().size() : 0;
        r.createdAt = s.getCreatedAt();
        return r;
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public String getDescription() { return description; }
    public String getOwnerName() { return ownerName; }
    public String getOwnerEmail() { return ownerEmail; }
    public String getAddress() { return address; }
    public String getEmail() { return email; }
    public boolean isOpen() { return open; }
    public int getProductCount() { return productCount; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    public void setId(Long id) { this.id = id; }
    public void setName(String name) { this.name = name; }
    public void setDescription(String description) { this.description = description; }
    public void setOwnerName(String ownerName) { this.ownerName = ownerName; }
    public void setOwnerEmail(String ownerEmail) { this.ownerEmail = ownerEmail; }
    public void setAddress(String address) { this.address = address; }
    public void setEmail(String email) { this.email = email; }
    public void setOpen(boolean open) { this.open = open; }
    public void setProductCount(int productCount) { this.productCount = productCount; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}

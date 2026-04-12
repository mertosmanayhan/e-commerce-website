package com.datapulse.ecommerce.dto.response;

import com.datapulse.ecommerce.entity.User;
import java.time.LocalDateTime;

public class UserResponse {
    private Long id; private String fullName, email, role, gender, city, country; private Integer age;
    private Boolean enabled; private LocalDateTime createdAt;
    public UserResponse() {}

    public Long getId() { return id; } public void setId(Long v) { this.id = v; }
    public String getFullName() { return fullName; } public void setFullName(String v) { this.fullName = v; }
    public String getEmail() { return email; } public void setEmail(String v) { this.email = v; }
    public String getRole() { return role; } public void setRole(String v) { this.role = v; }
    public String getGender() { return gender; } public void setGender(String v) { this.gender = v; }
    public Integer getAge() { return age; } public void setAge(Integer v) { this.age = v; }
    public String getCity() { return city; } public void setCity(String v) { this.city = v; }
    public String getCountry() { return country; } public void setCountry(String v) { this.country = v; }
    public Boolean getEnabled() { return enabled; } public void setEnabled(Boolean v) { this.enabled = v; }
    public LocalDateTime getCreatedAt() { return createdAt; } public void setCreatedAt(LocalDateTime v) { this.createdAt = v; }

    public static UserResponse fromEntity(User u) {
        UserResponse r = new UserResponse();
        r.id=u.getId(); r.fullName=u.getFullName(); r.email=u.getEmail(); r.role=u.getRole().name();
        r.gender=u.getGender(); r.age=u.getAge(); r.city=u.getCity(); r.country=u.getCountry();
        r.enabled=u.getEnabled(); r.createdAt=u.getCreatedAt();
        return r;
    }
}

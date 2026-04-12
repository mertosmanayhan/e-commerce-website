package com.datapulse.ecommerce.entity;

import com.datapulse.ecommerce.entity.enums.Role;
import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String fullName;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(nullable = false)
    private String password;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role;

    private String gender;
    private Integer age;
    private String city;
    private String country;

    @Column(nullable = false)
    private Boolean enabled = true;

    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    public User() {}

    public User(Long id, String fullName, String email, String password, Role role,
                String gender, Integer age, String city, String country, Boolean enabled) {
        this.id = id;
        this.fullName = fullName;
        this.email = email;
        this.password = password;
        this.role = role;
        this.gender = gender;
        this.age = age;
        this.city = city;
        this.country = country;
        this.enabled = enabled;
    }

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        if (this.enabled == null) this.enabled = true;
    }

    // Getters & Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getFullName() { return fullName; }
    public void setFullName(String fullName) { this.fullName = fullName; }
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
    public Role getRole() { return role; }
    public void setRole(Role role) { this.role = role; }
    public String getGender() { return gender; }
    public void setGender(String gender) { this.gender = gender; }
    public Integer getAge() { return age; }
    public void setAge(Integer age) { this.age = age; }
    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }
    public String getCountry() { return country; }
    public void setCountry(String country) { this.country = country; }
    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    // Builder
    public static UserBuilder builder() { return new UserBuilder(); }
    public static class UserBuilder {
        private Long id; private String fullName; private String email; private String password;
        private Role role; private String gender; private Integer age; private String city;
        private String country; private Boolean enabled = true;
        public UserBuilder id(Long id) { this.id = id; return this; }
        public UserBuilder fullName(String v) { this.fullName = v; return this; }
        public UserBuilder email(String v) { this.email = v; return this; }
        public UserBuilder password(String v) { this.password = v; return this; }
        public UserBuilder role(Role v) { this.role = v; return this; }
        public UserBuilder gender(String v) { this.gender = v; return this; }
        public UserBuilder age(Integer v) { this.age = v; return this; }
        public UserBuilder city(String v) { this.city = v; return this; }
        public UserBuilder country(String v) { this.country = v; return this; }
        public UserBuilder enabled(Boolean v) { this.enabled = v; return this; }
        public User build() { return new User(id, fullName, email, password, role, gender, age, city, country, enabled); }
    }
}

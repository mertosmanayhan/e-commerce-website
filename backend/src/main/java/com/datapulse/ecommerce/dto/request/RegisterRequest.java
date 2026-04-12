package com.datapulse.ecommerce.dto.request;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class RegisterRequest {
    @NotBlank private String fullName;
    @NotBlank @Email private String email;
    @NotBlank @Size(min = 6) private String password;
    private String role, gender, city, country;
    private Integer age;
    public String getFullName() { return fullName; } public void setFullName(String v) { this.fullName = v; }
    public String getEmail() { return email; } public void setEmail(String v) { this.email = v; }
    public String getPassword() { return password; } public void setPassword(String v) { this.password = v; }
    public String getRole() { return role; } public void setRole(String v) { this.role = v; }
    public String getGender() { return gender; } public void setGender(String v) { this.gender = v; }
    public Integer getAge() { return age; } public void setAge(Integer v) { this.age = v; }
    public String getCity() { return city; } public void setCity(String v) { this.city = v; }
    public String getCountry() { return country; } public void setCountry(String v) { this.country = v; }
}

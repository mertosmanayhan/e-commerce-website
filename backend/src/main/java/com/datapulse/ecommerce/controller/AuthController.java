package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.request.LoginRequest;
import com.datapulse.ecommerce.dto.request.RegisterRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.JwtResponse;
import com.datapulse.ecommerce.dto.response.UserResponse;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import java.util.Map;

@RestController @RequestMapping("/api/auth") @Tag(name="Authentication")
public class AuthController {
    private final AuthService authService; private final UserRepository userRepository;
    public AuthController(AuthService as, UserRepository ur) { this.authService=as; this.userRepository=ur; }

    @PostMapping("/register") @Operation(summary="Register a new user")
    public ResponseEntity<ApiResponse<JwtResponse>> register(@Valid @RequestBody RegisterRequest req) { return ResponseEntity.ok(ApiResponse.success("Registration successful", authService.register(req))); }

    @PostMapping("/login") @Operation(summary="Login")
    public ResponseEntity<ApiResponse<JwtResponse>> login(@Valid @RequestBody LoginRequest req) { return ResponseEntity.ok(ApiResponse.success("Login successful", authService.login(req))); }

    @PostMapping("/refresh") @Operation(summary="Refresh token")
    public ResponseEntity<ApiResponse<JwtResponse>> refresh(@RequestBody Map<String,String> body) { return ResponseEntity.ok(ApiResponse.success("Token refreshed", authService.refreshToken(body.get("refreshToken")))); }

    @GetMapping("/me") @Operation(summary="Get current user")
    public ResponseEntity<ApiResponse<UserResponse>> getCurrentUser(@AuthenticationPrincipal UserPrincipal principal) {
        User user = userRepository.findById(principal.getId()).orElseThrow(); return ResponseEntity.ok(ApiResponse.success(UserResponse.fromEntity(user)));
    }

    @PostMapping("/reset-password") @Operation(summary="Reset password")
    public ResponseEntity<ApiResponse<Void>> resetPassword(@RequestBody Map<String,String> body) {
        String email = body.get("email");
        String newPassword = body.get("newPassword");
        if (email == null || newPassword == null) throw new IllegalArgumentException("Email and newPassword are required");
        authService.resetPassword(email, newPassword);
        return ResponseEntity.ok(ApiResponse.success("Password reset successful", null));
    }

    @PutMapping("/profile") @Operation(summary="Update own profile")
    public ResponseEntity<ApiResponse<UserResponse>> updateProfile(
            @AuthenticationPrincipal UserPrincipal principal,
            @RequestBody Map<String,Object> body) {
        User user = userRepository.findById(principal.getId()).orElseThrow();
        if (body.containsKey("fullName") && body.get("fullName") != null) user.setFullName(body.get("fullName").toString());
        if (body.containsKey("gender")   && body.get("gender")   != null) user.setGender(body.get("gender").toString());
        if (body.containsKey("city")     && body.get("city")     != null) user.setCity(body.get("city").toString());
        if (body.containsKey("country")  && body.get("country")  != null) user.setCountry(body.get("country").toString());
        if (body.containsKey("age")      && body.get("age")      != null) user.setAge(Integer.valueOf(body.get("age").toString()));
        userRepository.save(user);
        return ResponseEntity.ok(ApiResponse.success("Profile updated", UserResponse.fromEntity(user)));
    }
}

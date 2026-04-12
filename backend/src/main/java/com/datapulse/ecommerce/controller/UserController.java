package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.UserResponse;
import com.datapulse.ecommerce.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController @RequestMapping("/api/users") @PreAuthorize("hasRole('ADMIN')") @Tag(name="User Management")
public class UserController {
    private final UserService userService;
    public UserController(UserService us) { this.userService = us; }
    @GetMapping @Operation(summary="List all users") public ResponseEntity<ApiResponse<List<UserResponse>>> getAll() { return ResponseEntity.ok(ApiResponse.success(userService.getAllUsers())); }
    @GetMapping("/{id}") @Operation(summary="Get user") public ResponseEntity<ApiResponse<UserResponse>> getById(@PathVariable Long id) { return ResponseEntity.ok(ApiResponse.success(userService.getUserById(id))); }
    @PutMapping("/{id}") @Operation(summary="Update user") public ResponseEntity<ApiResponse<UserResponse>> update(@PathVariable Long id, @RequestBody UserResponse req) { return ResponseEntity.ok(ApiResponse.success(userService.updateUser(id, req))); }
    @DeleteMapping("/{id}") @Operation(summary="Delete user") public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) { userService.deleteUser(id); return ResponseEntity.ok(ApiResponse.success("Deleted",null)); }
    @PatchMapping("/{id}/suspend") @Operation(summary="Toggle suspend") public ResponseEntity<ApiResponse<UserResponse>> toggle(@PathVariable Long id) { return ResponseEntity.ok(ApiResponse.success(userService.toggleUserStatus(id))); }
}

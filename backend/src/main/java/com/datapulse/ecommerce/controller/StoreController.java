package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.request.StoreRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.StoreResponse;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.StoreService;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/stores")
@Tag(name = "Stores")
public class StoreController {
    private final StoreService storeService;

    public StoreController(StoreService ss) { this.storeService = ss; }

    @GetMapping
    @PreAuthorize("hasAnyRole('CORPORATE', 'ADMIN')")
    public ResponseEntity<ApiResponse<List<StoreResponse>>> getAll(
            @AuthenticationPrincipal UserPrincipal principal) {
        List<StoreResponse> stores;
        if ("ADMIN".equals(principal.getRole())) {
            stores = storeService.getAllStores();
        } else {
            // CORPORATE: sadece kendi mağazaları
            stores = storeService.getStoresByOwner(principal.getId());
        }
        return ResponseEntity.ok(ApiResponse.success(stores));
    }

    @GetMapping("/{id}")
    @PreAuthorize("hasAnyRole('CORPORATE', 'ADMIN')")
    public ResponseEntity<ApiResponse<StoreResponse>> getById(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(storeService.getStoreById(id)));
    }

    @PostMapping
    @PreAuthorize("hasRole('CORPORATE')")
    public ResponseEntity<ApiResponse<StoreResponse>> create(@Valid @RequestBody StoreRequest req) {
        return ResponseEntity.ok(ApiResponse.success("Created", storeService.createStore(req)));
    }

    @PutMapping("/{id}")
    @PreAuthorize("hasAnyRole('CORPORATE', 'ADMIN')")
    public ResponseEntity<ApiResponse<StoreResponse>> update(
            @PathVariable Long id, @Valid @RequestBody StoreRequest req) {
        return ResponseEntity.ok(ApiResponse.success("Updated", storeService.updateStore(id, req)));
    }

    @PatchMapping("/{id}/toggle")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<ApiResponse<StoreResponse>> toggle(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(storeService.toggleStoreStatus(id)));
    }
}

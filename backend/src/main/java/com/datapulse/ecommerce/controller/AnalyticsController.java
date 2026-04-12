package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.DashboardResponse;
import com.datapulse.ecommerce.dto.response.IndividualAnalyticsResponse;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.AnalyticsService;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/analytics")
@Tag(name = "Analytics")
public class AnalyticsController {

    private final AnalyticsService analyticsService;

    public AnalyticsController(AnalyticsService as) {
        this.analyticsService = as;
    }

    @GetMapping("/dashboard")
    @PreAuthorize("hasAnyRole('CORPORATE', 'ADMIN')")
    public ResponseEntity<ApiResponse<DashboardResponse>> getDashboard(
            Authentication auth,
            @RequestParam(defaultValue="30") int days) {
        UserPrincipal principal = (UserPrincipal) auth.getPrincipal();
        DashboardResponse data = principal.getRole().equals("ADMIN")
                ? analyticsService.getDashboardData(days)
                : analyticsService.getStoreDashboardData(principal.getId(), days);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @GetMapping("/individual")
    @PreAuthorize("hasAnyRole('INDIVIDUAL', 'ADMIN')")
    public ResponseEntity<ApiResponse<IndividualAnalyticsResponse>> getIndividual(
            Authentication auth,
            @RequestParam(defaultValue="30") int days) {
        UserPrincipal principal = (UserPrincipal) auth.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                analyticsService.getIndividualAnalytics(principal.getId(), days)));
    }

    @GetMapping("/customers")
    @PreAuthorize("hasAnyRole('CORPORATE', 'ADMIN')")
    public ResponseEntity<ApiResponse<?>> getCustomerSegments(Authentication auth) {
        UserPrincipal principal = (UserPrincipal) auth.getPrincipal();
        return ResponseEntity.ok(ApiResponse.success(
                analyticsService.getCustomerSegments(principal.getId(), principal.getRole())));
    }
}

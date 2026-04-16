package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.ShipmentResponse;
import com.datapulse.ecommerce.entity.Shipment;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.ShipmentService;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController @RequestMapping("/api/shipments") @Tag(name="Shipments")
public class ShipmentController {
    private final ShipmentService shipmentService;
    public ShipmentController(ShipmentService ss) { this.shipmentService = ss; }

    @GetMapping
    public ResponseEntity<ApiResponse<List<ShipmentResponse>>> all(@AuthenticationPrincipal UserPrincipal principal) {
        String role = principal.getRole();
        List<Shipment> shipments;
        if ("ADMIN".equals(role)) {
            shipments = shipmentService.getAllShipments();
        } else if ("CORPORATE".equals(role)) {
            shipments = shipmentService.getShipmentsByStoreOwner(principal.getId());
        } else {
            shipments = shipmentService.getShipmentsByUser(principal.getId());
        }
        List<ShipmentResponse> result = shipments.stream().map(ShipmentResponse::fromEntity).toList();
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @GetMapping("/order/{orderId}") public ResponseEntity<ApiResponse<ShipmentResponse>> byOrder(@PathVariable Long orderId) { return ResponseEntity.ok(ApiResponse.success(ShipmentResponse.fromEntity(shipmentService.getShipmentByOrderId(orderId)))); }
    @GetMapping("/track/{trackingNumber}") public ResponseEntity<ApiResponse<ShipmentResponse>> track(@PathVariable String trackingNumber) { return ResponseEntity.ok(ApiResponse.success(ShipmentResponse.fromEntity(shipmentService.getShipmentByTrackingNumber(trackingNumber)))); }
    @PatchMapping("/{id}/status") @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')") public ResponseEntity<ApiResponse<ShipmentResponse>> updateStatus(@PathVariable Long id, @RequestBody Map<String,String> body) { return ResponseEntity.ok(ApiResponse.success(ShipmentResponse.fromEntity(shipmentService.updateShipmentStatus(id,body.get("status"))))); }
}

package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.entity.Shipment;
import com.datapulse.ecommerce.service.ShipmentService;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController @RequestMapping("/api/shipments") @Tag(name="Shipments")
public class ShipmentController {
    private final ShipmentService shipmentService;
    public ShipmentController(ShipmentService ss) { this.shipmentService = ss; }
    @GetMapping public ResponseEntity<ApiResponse<List<Shipment>>> all() { return ResponseEntity.ok(ApiResponse.success(shipmentService.getAllShipments())); }
    @GetMapping("/order/{orderId}") public ResponseEntity<ApiResponse<Shipment>> byOrder(@PathVariable Long orderId) { return ResponseEntity.ok(ApiResponse.success(shipmentService.getShipmentByOrderId(orderId))); }
    @GetMapping("/track/{trackingNumber}") public ResponseEntity<ApiResponse<Shipment>> track(@PathVariable String trackingNumber) { return ResponseEntity.ok(ApiResponse.success(shipmentService.getShipmentByTrackingNumber(trackingNumber))); }
    @PatchMapping("/{id}/status") @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')") public ResponseEntity<ApiResponse<Shipment>> updateStatus(@PathVariable Long id, @RequestBody Map<String,String> body) { return ResponseEntity.ok(ApiResponse.success(shipmentService.updateShipmentStatus(id,body.get("status")))); }
}

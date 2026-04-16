package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.request.CreateOrderRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.OrderResponse;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.data.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Map;

@RestController @RequestMapping("/api/orders") @Tag(name="Orders")
public class OrderController {
    private final OrderService orderService;
    public OrderController(OrderService os) { this.orderService = os; }

    @GetMapping @Operation(summary="List orders")
    public ResponseEntity<ApiResponse<Page<OrderResponse>>> getOrders(
            @AuthenticationPrincipal UserPrincipal principal,
            @RequestParam(defaultValue="0") int page,
            @RequestParam(defaultValue="20") int size,
            @RequestParam(required=false) String status) {
        Pageable pageable = PageRequest.of(page, size, Sort.by("orderDate").descending());
        Page<OrderResponse> orders;
        String role = principal.getRole();
        if ("ADMIN".equals(role)) {
            orders = orderService.getAllOrders(pageable);
        } else if ("CORPORATE".equals(role)) {
            // Corporate: kendi mağazasının ürünlerini içeren siparişler
            orders = orderService.getOrdersByStoreOwner(principal.getId(), pageable);
        } else {
            orders = orderService.getOrdersByUser(principal.getId(), pageable);
        }
        return ResponseEntity.ok(ApiResponse.success(orders));
    }

    @GetMapping("/export/csv") @Operation(summary="Export orders as CSV")
    public void exportCsv(@AuthenticationPrincipal UserPrincipal principal, HttpServletResponse response) throws IOException {
        response.setContentType("text/csv");
        response.setHeader("Content-Disposition", "attachment; filename=\"orders.csv\"");
        Pageable pageable = PageRequest.of(0, 10000, Sort.by("orderDate").descending());
        Page<OrderResponse> orders = principal.getRole().equals("ADMIN")
                ? orderService.getAllOrders(pageable)
                : orderService.getOrdersByUser(principal.getId(), pageable);
        PrintWriter w = response.getWriter();
        w.println("Sipariş No,Tarih,Durum,Toplam,Ödeme Yöntemi");
        for (OrderResponse o : orders.getContent()) {
            w.printf("%s,%s,%s,%.2f,%s%n",
                o.getOrderNumber(),
                o.getOrderDate() != null ? o.getOrderDate().toString().substring(0,10) : "",
                o.getStatus(),
                o.getTotalAmount() != null ? o.getTotalAmount().doubleValue() : 0.0,
                o.getPaymentMethod() != null ? o.getPaymentMethod() : "");
        }
        w.flush();
    }

    @GetMapping("/{id}") @Operation(summary="Get order") public ResponseEntity<ApiResponse<OrderResponse>> getById(@PathVariable Long id) { return ResponseEntity.ok(ApiResponse.success(orderService.getOrderById(id))); }
    @PostMapping @PreAuthorize("hasRole('INDIVIDUAL')") @Operation(summary="Place order") public ResponseEntity<ApiResponse<OrderResponse>> create(@Valid @RequestBody CreateOrderRequest req) { return ResponseEntity.ok(ApiResponse.success("Order placed",orderService.createOrder(req))); }
    @PatchMapping("/{id}/status") @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')") @Operation(summary="Update status") public ResponseEntity<ApiResponse<OrderResponse>> updateStatus(@PathVariable Long id, @RequestBody Map<String,String> body) { return ResponseEntity.ok(ApiResponse.success(orderService.updateOrderStatus(id,body.get("status")))); }
    @GetMapping("/store/{storeId}") @PreAuthorize("hasAnyRole('CORPORATE','ADMIN')") public ResponseEntity<ApiResponse<Page<OrderResponse>>> byStore(@PathVariable Long storeId, @RequestParam(defaultValue="0") int page, @RequestParam(defaultValue="20") int size) { return ResponseEntity.ok(ApiResponse.success(orderService.getOrdersByStore(storeId,PageRequest.of(page,size,Sort.by("orderDate").descending())))); }
}

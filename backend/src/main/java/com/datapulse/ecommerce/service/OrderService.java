package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.CreateOrderRequest;
import com.datapulse.ecommerce.dto.response.OrderResponse;
import com.datapulse.ecommerce.entity.*;
import com.datapulse.ecommerce.entity.enums.OrderStatus;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.OrderRepository;
import com.datapulse.ecommerce.repository.ProductRepository;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.concurrent.ThreadLocalRandom;

@Service
public class OrderService {
    private final OrderRepository orderRepository; private final ProductRepository productRepository; private final UserRepository userRepository;
    public OrderService(OrderRepository or, ProductRepository pr, UserRepository ur) { this.orderRepository=or; this.productRepository=pr; this.userRepository=ur; }

    public Page<OrderResponse> getOrdersByUser(Long userId, Pageable p) { return orderRepository.findByUserId(userId, p).map(OrderResponse::fromEntity); }
    public Page<OrderResponse> getOrdersByStore(Long storeId, Pageable p) { return orderRepository.findByStoreId(storeId, p).map(OrderResponse::fromEntity); }
    public Page<OrderResponse> getAllOrders(Pageable p) { return orderRepository.findAll(p).map(OrderResponse::fromEntity); }
    public OrderResponse getOrderById(Long id) { return OrderResponse.fromEntity(orderRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Order","id",id))); }

    @Transactional public OrderResponse createOrder(CreateOrderRequest req) {
        UserPrincipal principal = (UserPrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        User user = userRepository.findById(principal.getId()).orElseThrow();
        String orderNumber = "ORD-" + (100000 + ThreadLocalRandom.current().nextInt(900000));
        Order order = Order.builder().orderNumber(orderNumber).user(user).status(OrderStatus.PENDING).paymentMethod(req.getPaymentMethod()).items(new ArrayList<>()).build();
        BigDecimal total = BigDecimal.ZERO;
        for (CreateOrderRequest.OrderItemRequest ir : req.getItems()) {
            Product product = productRepository.findById(ir.getProductId()).orElseThrow(() -> new ResourceNotFoundException("Product","id",ir.getProductId()));
            if (product.getStock() < ir.getQuantity()) throw new IllegalArgumentException("Insufficient stock for: " + product.getName());
            product.setStock(product.getStock() - ir.getQuantity()); productRepository.save(product);
            OrderItem oi = OrderItem.builder().order(order).product(product).quantity(ir.getQuantity()).unitPrice(product.getPrice()).build();
            order.getItems().add(oi);
            total = total.add(product.getPrice().multiply(BigDecimal.valueOf(ir.getQuantity())));
        }
        order.setTotalAmount(total); orderRepository.save(order); return OrderResponse.fromEntity(order);
    }

    @Transactional public OrderResponse updateOrderStatus(Long id, String status) {
        Order order = orderRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Order","id",id));
        try { order.setStatus(OrderStatus.valueOf(status.toUpperCase())); } catch (IllegalArgumentException e) { throw new IllegalArgumentException("Invalid status: " + status); }
        orderRepository.save(order); return OrderResponse.fromEntity(order);
    }
}

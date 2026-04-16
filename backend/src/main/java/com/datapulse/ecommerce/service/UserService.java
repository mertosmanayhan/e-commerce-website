package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.response.UserResponse;
import com.datapulse.ecommerce.entity.Order;
import com.datapulse.ecommerce.entity.Store;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.*;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final ReviewRepository reviewRepository;
    private final CartItemRepository cartItemRepository;
    private final WishlistItemRepository wishlistItemRepository;
    private final CustomerProfileRepository customerProfileRepository;
    private final OrderRepository orderRepository;
    private final StoreRepository storeRepository;

    @PersistenceContext
    private EntityManager em;

    public UserService(UserRepository ur, ReviewRepository rr,
                       CartItemRepository cr, WishlistItemRepository wr,
                       CustomerProfileRepository cpr, OrderRepository or,
                       StoreRepository sr) {
        this.userRepository = ur;
        this.reviewRepository = rr;
        this.cartItemRepository = cr;
        this.wishlistItemRepository = wr;
        this.customerProfileRepository = cpr;
        this.orderRepository = or;
        this.storeRepository = sr;
    }

    public List<UserResponse> getAllUsers() {
        return userRepository.findAll().stream().map(UserResponse::fromEntity).toList();
    }

    public UserResponse getUserById(Long id) {
        return UserResponse.fromEntity(userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", id)));
    }

    @Transactional
    public UserResponse updateUser(Long id, UserResponse req) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", id));
        if (req.getFullName() != null) user.setFullName(req.getFullName());
        if (req.getGender() != null) user.setGender(req.getGender());
        if (req.getAge() != null) user.setAge(req.getAge());
        if (req.getCity() != null) user.setCity(req.getCity());
        if (req.getCountry() != null) user.setCountry(req.getCountry());
        userRepository.save(user);
        return UserResponse.fromEntity(user);
    }

    @Transactional
    public void deleteUser(Long id) {
        if (!userRepository.existsById(id)) throw new ResourceNotFoundException("User", "id", id);

        // 1. Yorumları sil
        reviewRepository.deleteAll(reviewRepository.findByUserId(id));

        // 2. Sepet öğelerini sil
        cartItemRepository.deleteAll(cartItemRepository.findByUserId(id));

        // 3. Favori öğeleri sil
        wishlistItemRepository.deleteAll(wishlistItemRepository.findByUserId(id));

        // 4. Müşteri profilini sil
        customerProfileRepository.findByUserId(id).ifPresent(customerProfileRepository::delete);

        // 5. Siparişleri sil (order_items + shipment cascade ile silinir)
        List<Order> orders = orderRepository.findByUserId(id, PageRequest.of(0, Integer.MAX_VALUE)).getContent();
        orderRepository.deleteAll(orders);

        // 6. Mağaza sahibi ise mağazaları sil (ürünler cascade ile silinir)
        List<Store> stores = storeRepository.findByOwnerId(id);
        storeRepository.deleteAll(stores);

        // 7. Kullanıcıyı sil
        em.flush();
        userRepository.deleteById(id);
    }

    @Transactional
    public UserResponse toggleUserStatus(Long id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("User", "id", id));
        user.setEnabled(!user.getEnabled());
        userRepository.save(user);
        return UserResponse.fromEntity(user);
    }
}

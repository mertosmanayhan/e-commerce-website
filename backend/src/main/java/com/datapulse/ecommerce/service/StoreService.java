package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.StoreRequest;
import com.datapulse.ecommerce.dto.response.StoreResponse;
import com.datapulse.ecommerce.entity.Store;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.entity.enums.Role;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.StoreRepository;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class StoreService {
    private final StoreRepository storeRepository;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public StoreService(StoreRepository sr, UserRepository ur, PasswordEncoder pe) {
        this.storeRepository = sr;
        this.userRepository = ur;
        this.passwordEncoder = pe;
    }

    @Transactional(readOnly = true)
    public List<StoreResponse> getAllStores() {
        return storeRepository.findAll().stream()
                .map(StoreResponse::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public StoreResponse getStoreById(Long id) {
        Store s = storeRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Store", "id", id));
        return StoreResponse.fromEntity(s);
    }

    @Transactional(readOnly = true)
    public List<StoreResponse> getStoresByOwner(Long ownerId) {
        return storeRepository.findByOwnerId(ownerId).stream()
                .map(StoreResponse::fromEntity)
                .collect(Collectors.toList());
    }

    @Transactional
    public StoreResponse createStore(StoreRequest req) {
        UserPrincipal principal = (UserPrincipal) SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        User owner;

        if ("ADMIN".equals(principal.getRole()) && req.getOwnerEmail() != null && !req.getOwnerEmail().isBlank()) {
            // Admin creates store for a specific owner by email — create new CORPORATE user if not exists
            owner = userRepository.findByEmail(req.getOwnerEmail()).orElseGet(() -> {
                User newUser = User.builder()
                        .fullName(req.getOwnerEmail().split("@")[0])
                        .email(req.getOwnerEmail())
                        .password(passwordEncoder.encode(
                                req.getOwnerPassword() != null && !req.getOwnerPassword().isBlank()
                                        ? req.getOwnerPassword() : "Temp1234!"))
                        .role(Role.CORPORATE)
                        .enabled(true)
                        .build();
                return userRepository.save(newUser);
            });
        } else {
            owner = userRepository.findById(principal.getId()).orElseThrow();
        }

        Store s = Store.builder()
                .name(req.getName())
                .description(req.getDescription())
                .address(req.getAddress())
                .email(req.getEmail())
                .owner(owner)
                .isOpen(true)
                .build();
        return StoreResponse.fromEntity(storeRepository.save(s));
    }

    @Transactional
    public StoreResponse updateStore(Long id, StoreRequest req) {
        Store s = storeRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Store", "id", id));
        s.setName(req.getName());
        s.setDescription(req.getDescription());
        if (req.getAddress() != null) s.setAddress(req.getAddress());
        if (req.getEmail() != null)   s.setEmail(req.getEmail());
        return StoreResponse.fromEntity(storeRepository.save(s));
    }

    @Transactional
    public StoreResponse toggleStoreStatus(Long id) {
        Store s = storeRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Store", "id", id));
        s.setIsOpen(!s.getIsOpen());
        return StoreResponse.fromEntity(storeRepository.save(s));
    }

    @Transactional
    public void deleteStore(Long id) {
        if (!storeRepository.existsById(id))
            throw new ResourceNotFoundException("Store", "id", id);
        storeRepository.deleteById(id);
    }
}

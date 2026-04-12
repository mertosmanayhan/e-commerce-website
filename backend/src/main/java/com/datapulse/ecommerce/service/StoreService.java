package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.StoreRequest;
import com.datapulse.ecommerce.dto.response.StoreResponse;
import com.datapulse.ecommerce.entity.Store;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.StoreRepository;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class StoreService {
    private final StoreRepository storeRepository;
    private final UserRepository userRepository;

    public StoreService(StoreRepository sr, UserRepository ur) {
        this.storeRepository = sr;
        this.userRepository = ur;
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
        User owner = userRepository.findById(principal.getId()).orElseThrow();
        Store s = Store.builder().name(req.getName()).description(req.getDescription()).owner(owner).isOpen(true).build();
        return StoreResponse.fromEntity(storeRepository.save(s));
    }

    @Transactional
    public StoreResponse updateStore(Long id, StoreRequest req) {
        Store s = storeRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Store", "id", id));
        s.setName(req.getName());
        s.setDescription(req.getDescription());
        return StoreResponse.fromEntity(storeRepository.save(s));
    }

    @Transactional
    public StoreResponse toggleStoreStatus(Long id) {
        Store s = storeRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Store", "id", id));
        s.setIsOpen(!s.getIsOpen());
        return StoreResponse.fromEntity(storeRepository.save(s));
    }
}

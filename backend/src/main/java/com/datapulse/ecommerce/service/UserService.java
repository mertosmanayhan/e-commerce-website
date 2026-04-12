package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.response.UserResponse;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class UserService {
    private final UserRepository userRepository;
    public UserService(UserRepository ur) { this.userRepository = ur; }

    public List<UserResponse> getAllUsers() { return userRepository.findAll().stream().map(UserResponse::fromEntity).toList(); }

    public UserResponse getUserById(Long id) {
        return UserResponse.fromEntity(userRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("User", "id", id)));
    }

    @Transactional public UserResponse updateUser(Long id, UserResponse req) {
        User user = userRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("User", "id", id));
        if (req.getFullName()!=null) user.setFullName(req.getFullName());
        if (req.getGender()!=null) user.setGender(req.getGender());
        if (req.getAge()!=null) user.setAge(req.getAge());
        if (req.getCity()!=null) user.setCity(req.getCity());
        if (req.getCountry()!=null) user.setCountry(req.getCountry());
        userRepository.save(user); return UserResponse.fromEntity(user);
    }

    @Transactional public void deleteUser(Long id) {
        if (!userRepository.existsById(id)) throw new ResourceNotFoundException("User", "id", id);
        userRepository.deleteById(id);
    }

    @Transactional public UserResponse toggleUserStatus(Long id) {
        User user = userRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("User", "id", id));
        user.setEnabled(!user.getEnabled()); userRepository.save(user); return UserResponse.fromEntity(user);
    }
}

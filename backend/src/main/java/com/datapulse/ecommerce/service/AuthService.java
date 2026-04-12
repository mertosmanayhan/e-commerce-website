package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.LoginRequest;
import com.datapulse.ecommerce.dto.request.RegisterRequest;
import com.datapulse.ecommerce.dto.response.JwtResponse;
import com.datapulse.ecommerce.dto.response.UserResponse;
import com.datapulse.ecommerce.entity.User;
import com.datapulse.ecommerce.entity.enums.Role;
import com.datapulse.ecommerce.repository.UserRepository;
import com.datapulse.ecommerce.security.JwtTokenProvider;
import com.datapulse.ecommerce.security.UserPrincipal;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {
    private final AuthenticationManager authenticationManager;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;

    public AuthService(AuthenticationManager am, UserRepository ur, PasswordEncoder pe, JwtTokenProvider tp) {
        this.authenticationManager=am; this.userRepository=ur; this.passwordEncoder=pe; this.tokenProvider=tp;
    }

    @Transactional
    public JwtResponse register(RegisterRequest req) {
        if (userRepository.existsByEmail(req.getEmail()))
            throw new IllegalArgumentException("Email already registered: " + req.getEmail());

        Role role = Role.INDIVIDUAL;
        if (req.getRole() != null) { try { role = Role.valueOf(req.getRole().toUpperCase()); } catch (IllegalArgumentException ignored) {} }

        User user = User.builder().fullName(req.getFullName()).email(req.getEmail())
                .password(passwordEncoder.encode(req.getPassword())).role(role)
                .gender(req.getGender()).age(req.getAge()).city(req.getCity()).country(req.getCountry()).enabled(true).build();
        userRepository.save(user);

        Authentication auth = authenticationManager.authenticate(new UsernamePasswordAuthenticationToken(req.getEmail(), req.getPassword()));
        SecurityContextHolder.getContext().setAuthentication(auth);
        return JwtResponse.builder().accessToken(tokenProvider.generateAccessToken(auth)).refreshToken(tokenProvider.generateRefreshToken(auth))
                .tokenType("Bearer").expiresIn(tokenProvider.getAccessTokenExpirationMs()).user(UserResponse.fromEntity(user)).build();
    }

    public JwtResponse login(LoginRequest req) {
        Authentication auth = authenticationManager.authenticate(new UsernamePasswordAuthenticationToken(req.getEmail(), req.getPassword()));
        SecurityContextHolder.getContext().setAuthentication(auth);
        UserPrincipal principal = (UserPrincipal) auth.getPrincipal();
        User user = userRepository.findById(principal.getId()).orElseThrow();
        return JwtResponse.builder().accessToken(tokenProvider.generateAccessToken(auth)).refreshToken(tokenProvider.generateRefreshToken(auth))
                .tokenType("Bearer").expiresIn(tokenProvider.getAccessTokenExpirationMs()).user(UserResponse.fromEntity(user)).build();
    }

    public JwtResponse refreshToken(String refreshToken) {
        if (!tokenProvider.validateToken(refreshToken)) throw new IllegalArgumentException("Invalid refresh token");
        Long userId = tokenProvider.getUserIdFromToken(refreshToken);
        User user = userRepository.findById(userId).orElseThrow(() -> new IllegalArgumentException("User not found"));
        String newAccessToken = tokenProvider.generateAccessTokenFromUserId(user.getId(), user.getEmail(), user.getRole().name());
        return JwtResponse.builder().accessToken(newAccessToken).refreshToken(refreshToken)
                .tokenType("Bearer").expiresIn(tokenProvider.getAccessTokenExpirationMs()).user(UserResponse.fromEntity(user)).build();
    }

    @Transactional
    public void resetPassword(String email, String newPassword) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new IllegalArgumentException("Bu e-posta adresiyle kayıtlı kullanıcı bulunamadı."));
        user.setPassword(passwordEncoder.encode(newPassword));
        userRepository.save(user);
    }
}

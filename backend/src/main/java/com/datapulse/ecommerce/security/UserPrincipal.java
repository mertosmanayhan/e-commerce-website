package com.datapulse.ecommerce.security;

import com.datapulse.ecommerce.entity.User;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import java.util.Collection;
import java.util.List;

public class UserPrincipal implements UserDetails {
    private Long id; private String fullName, email, password, role; private Boolean enabled;
    private Collection<? extends GrantedAuthority> authorities;

    public UserPrincipal(Long id, String fn, String e, String p, String r, Boolean en, Collection<? extends GrantedAuthority> a) {
        this.id=id; this.fullName=fn; this.email=e; this.password=p; this.role=r; this.enabled=en; this.authorities=a;
    }

    public static UserPrincipal create(User user) {
        List<GrantedAuthority> auth = List.of(new SimpleGrantedAuthority("ROLE_" + user.getRole().name()));
        return new UserPrincipal(user.getId(), user.getFullName(), user.getEmail(), user.getPassword(), user.getRole().name(), user.getEnabled(), auth);
    }

    public Long getId() { return id; }
    public String getFullName() { return fullName; }
    public String getEmail() { return email; }
    public String getRole() { return role; }
    @Override public String getPassword() { return password; }
    @Override public String getUsername() { return email; }
    @Override public Collection<? extends GrantedAuthority> getAuthorities() { return authorities; }
    @Override public boolean isAccountNonExpired() { return true; }
    @Override public boolean isAccountNonLocked() { return enabled; }
    @Override public boolean isCredentialsNonExpired() { return true; }
    @Override public boolean isEnabled() { return enabled; }
}

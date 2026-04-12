package com.datapulse.ecommerce.dto.response;

public class JwtResponse {
    private String accessToken, refreshToken, tokenType; private Long expiresIn; private UserResponse user;
    public JwtResponse() { this.tokenType = "Bearer"; }
    public JwtResponse(String at, String rt, String tt, Long ei, UserResponse u) { accessToken=at; refreshToken=rt; tokenType=tt; expiresIn=ei; user=u; }
    public String getAccessToken() { return accessToken; } public void setAccessToken(String v) { this.accessToken = v; }
    public String getRefreshToken() { return refreshToken; } public void setRefreshToken(String v) { this.refreshToken = v; }
    public String getTokenType() { return tokenType; } public void setTokenType(String v) { this.tokenType = v; }
    public Long getExpiresIn() { return expiresIn; } public void setExpiresIn(Long v) { this.expiresIn = v; }
    public UserResponse getUser() { return user; } public void setUser(UserResponse v) { this.user = v; }

    public static JwtResponseBuilder builder() { return new JwtResponseBuilder(); }
    public static class JwtResponseBuilder {
        private String at, rt, tt = "Bearer"; private Long ei; private UserResponse u;
        public JwtResponseBuilder accessToken(String v) { this.at = v; return this; }
        public JwtResponseBuilder refreshToken(String v) { this.rt = v; return this; }
        public JwtResponseBuilder tokenType(String v) { this.tt = v; return this; }
        public JwtResponseBuilder expiresIn(Long v) { this.ei = v; return this; }
        public JwtResponseBuilder user(UserResponse v) { this.u = v; return this; }
        public JwtResponse build() { return new JwtResponse(at, rt, tt, ei, u); }
    }
}

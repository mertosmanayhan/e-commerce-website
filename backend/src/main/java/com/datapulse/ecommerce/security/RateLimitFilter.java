package com.datapulse.ecommerce.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Simple in-memory rate limiter: max 30 requests/minute per IP for /api/chat endpoints.
 * For production, replace with Redis-backed Bucket4j or similar.
 */
@Component
public class RateLimitFilter implements Filter {

    private static final int MAX_REQUESTS = 30;
    private static final long WINDOW_MS   = 60_000L;

    private record WindowCounter(AtomicInteger count, long windowStart) {}

    private final Map<String, WindowCounter> ipCounters = new ConcurrentHashMap<>();

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse,
                         FilterChain chain) throws IOException, ServletException {

        HttpServletRequest  req  = (HttpServletRequest)  servletRequest;
        HttpServletResponse resp = (HttpServletResponse) servletResponse;

        if (req.getRequestURI().startsWith("/api/chat")) {
            String ip = getClientIp(req);
            long   now = System.currentTimeMillis();

            WindowCounter wc = ipCounters.compute(ip, (k, existing) -> {
                if (existing == null || (now - existing.windowStart()) >= WINDOW_MS) {
                    return new WindowCounter(new AtomicInteger(1), now);
                }
                existing.count().incrementAndGet();
                return existing;
            });

            if (wc.count().get() > MAX_REQUESTS) {
                resp.setStatus(429);
                resp.setContentType("application/json");
                resp.getWriter().write("{\"success\":false,\"message\":\"Çok fazla istek. Lütfen bir dakika bekleyin.\"}");
                return;
            }
        }

        chain.doFilter(servletRequest, servletResponse);
    }

    private String getClientIp(HttpServletRequest req) {
        String forwarded = req.getHeader("X-Forwarded-For");
        return (forwarded != null && !forwarded.isBlank())
                ? forwarded.split(",")[0].trim()
                : req.getRemoteAddr();
    }
}

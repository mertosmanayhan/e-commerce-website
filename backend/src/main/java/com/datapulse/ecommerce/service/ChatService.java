package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.repository.StoreRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * ChatService — orchestrates communication between Angular frontend,
 * Spring Boot security layer, and the Python LangGraph microservice.
 *
 * Responsibilities:
 *  • Resolve store_id for CORPORATE users from the stores table.
 *  • Build the enriched payload (message + role + user_id + store_id).
 *  • Forward the request to the Python AI service via HTTP POST.
 *  • Delegate direct SQL execution to SafeSqlExecutorService.
 */
@Service
public class ChatService {

    private static final Logger log = LoggerFactory.getLogger(ChatService.class);

    private final RestTemplate           restTemplate;
    private final SafeSqlExecutorService sqlExecutor;
    private final StoreRepository        storeRepository;

    @Value("${chatbot.service.url:http://localhost:8000}")
    private String chatbotServiceUrl;

    public ChatService(RestTemplate restTemplate,
                       SafeSqlExecutorService sqlExecutor,
                       StoreRepository storeRepository) {
        this.restTemplate    = restTemplate;
        this.sqlExecutor     = sqlExecutor;
        this.storeRepository = storeRepository;
    }

    /**
     * Forwards a chat message to the Python LangGraph service.
     *
     * @param question Natural-language question from the user
     * @param role     User role: INDIVIDUAL | CORPORATE | ADMIN
     * @param userId   Authenticated user's database ID
     * @return Map containing answer, sql, plotData fields from the AI service
     */
    public Map<String, Object> askAI(String question, String role, Long userId) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("message", question);
        payload.put("role",    role);
        payload.put("user_id", userId);

        // Resolve store_id for CORPORATE users
        if ("CORPORATE".equalsIgnoreCase(role) && userId != null) {
            storeRepository.findByOwnerId(userId)
                .stream()
                .findFirst()
                .ifPresent(store -> payload.put("store_id", store.getId()));
        }

        log.info("Forwarding to AI service — role={} userId={} store_id={}",
                 role, userId, payload.get("store_id"));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> request = new HttpEntity<>(payload, headers);

        try {
            @SuppressWarnings("unchecked")
            ResponseEntity<Map<String, Object>> response = restTemplate.exchange(
                chatbotServiceUrl + "/api/chat/ask",
                HttpMethod.POST,
                request,
                (Class<Map<String, Object>>) (Class<?>) Map.class
            );
            Map<String, Object> body = response.getBody();
            return body != null ? body : fallbackResponse();
        } catch (Exception e) {
            log.error("AI service unreachable: {}", e.getMessage());
            return fallbackResponse();
        }
    }

    /**
     * Executes a validated SQL query directly in Spring Boot (bypasses Python).
     * Used by the /api/chat/execute-sql endpoint.
     */
    public Map<String, Object> executeQuery(String sql) {
        return sqlExecutor.executeQuery(sql);
    }

    private Map<String, Object> fallbackResponse() {
        Map<String, Object> fb = new HashMap<>();
        fb.put("answer",
            "AI servisi şu an ulaşılamıyor.\n\n" +
            "Servisi başlatmak için:\n" +
            "  cd ai-agent && python app.py");
        fb.put("sql",      null);
        fb.put("plotData", null);
        return fb;
    }
}

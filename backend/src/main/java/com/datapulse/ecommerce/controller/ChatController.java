package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.request.ChatRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.service.ChatService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/chat")
@Tag(name = "AI Chatbot")
public class ChatController {

    private final RestTemplate restTemplate;
    private final ChatService  chatService;

    @Value("${chatbot.service.url:http://localhost:8000}")
    private String chatbotUrl;

    public ChatController(RestTemplate restTemplate, ChatService chatService) {
        this.restTemplate = restTemplate;
        this.chatService  = chatService;
    }

    /** Primary endpoint — proxies to Python LangGraph chatbot */
    @PostMapping("/ask")
    @Operation(summary = "Ask AI chatbot (Text2SQL)")
    public ResponseEntity<ApiResponse<Map<String, Object>>> ask(
            @RequestBody ChatRequest req,
            Authentication authentication) {
        try {
            Map<String, Object> body = new HashMap<>();
            body.put("message", req.getQuestion());

            String role   = "INDIVIDUAL";
            Long   userId = null;
            if (authentication != null && authentication.getPrincipal() instanceof
                    com.datapulse.ecommerce.security.UserPrincipal principal) {
                role   = principal.getRole();
                userId = principal.getId();
            }
            body.put("role", role);
            if (userId != null) body.put("user_id", userId);

            @SuppressWarnings("unchecked")
            Map<String, Object> response = restTemplate.postForObject(
                    chatbotUrl + "/api/chat/ask", body, Map.class);

            return ResponseEntity.ok(ApiResponse.success(response));

        } catch (Exception e) {
            // Python service unavailable — return helpful fallback
            Map<String, Object> fallback = new HashMap<>();
            fallback.put("answer",
                "AI servisi şu an ulaşılamıyor.\n\n" +
                "Chatbot'u başlatmak için:\n" +
                "cd chatbot-service && python main.py");
            fallback.put("sql", null);
            fallback.put("plotData", null);
            return ResponseEntity.ok(ApiResponse.success(fallback));
        }
    }

    /** Secondary endpoint — executes chatbot-generated SQL directly via Spring Boot */
    @PostMapping("/execute-sql")
    @Operation(summary = "Execute chatbot-generated SQL query (SELECT only)")
    public ResponseEntity<ApiResponse<Map<String, Object>>> executeSql(
            @RequestBody Map<String, String> body) {
        String sql = body.getOrDefault("sql", "").trim();
        if (sql.isEmpty()) {
            return ResponseEntity.badRequest()
                    .body(ApiResponse.error("SQL sorgusu boş olamaz."));
        }
        return ResponseEntity.ok(ApiResponse.success(chatService.executeQuery(sql)));
    }
}

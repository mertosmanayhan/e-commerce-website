package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.request.ChatRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.security.UserPrincipal;
import com.datapulse.ecommerce.service.ChatService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/chat")
@Tag(name = "AI Chatbot")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    /**
     * Primary endpoint — resolves caller identity, then proxies to Python LangGraph service.
     * Role-based data isolation is enforced inside ChatService (store_id resolution)
     * and inside the Python SQL Agent (WHERE clause injection).
     */
    @PostMapping("/ask")
    @Operation(summary = "Ask AI chatbot (Text2SQL)")
    public ResponseEntity<ApiResponse<Map<String, Object>>> ask(
            @RequestBody ChatRequest req,
            Authentication authentication) {

        String role   = "INDIVIDUAL";
        Long   userId = null;

        if (authentication != null
                && authentication.getPrincipal() instanceof UserPrincipal principal) {
            role   = principal.getRole();
            userId = principal.getId();
        }

        Map<String, Object> result = chatService.askAI(req.getQuestion(), role, userId);
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    /**
     * Secondary endpoint — executes chatbot-generated SQL directly via SafeSqlExecutorService.
     * Useful for debugging or when the frontend wants to re-run a cached query.
     */
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

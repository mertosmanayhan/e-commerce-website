package com.datapulse.ecommerce.controller;

import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.stripe.Stripe;
import com.stripe.exception.StripeException;
import com.stripe.model.PaymentIntent;
import com.stripe.param.PaymentIntentCreateParams;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/payment")
@Tag(name = "Payment")
public class PaymentController {

    @Value("${stripe.secret-key:}")
    private String stripeSecretKey;

    @Value("${stripe.publishable-key:pk_test_demo}")
    private String stripePublishableKey;

    private boolean isStripeConfigured() {
        return stripeSecretKey != null
            && stripeSecretKey.startsWith("sk_")
            && stripeSecretKey.length() > 40;
    }

    @GetMapping("/config")
    @Operation(summary = "Get Stripe publishable key")
    public ResponseEntity<ApiResponse<Map<String, String>>> getConfig() {
        return ResponseEntity.ok(ApiResponse.success(
            Map.of("publishableKey", stripePublishableKey)
        ));
    }

    @PostMapping("/create-intent")
    @Operation(summary = "Create Stripe PaymentIntent")
    public ResponseEntity<ApiResponse<Map<String, String>>> createPaymentIntent(
            @RequestBody Map<String, Object> body) {

        // Simülasyon modu: Stripe key yapılandırılmamışsa test clientSecret döndür
        if (!isStripeConfigured()) {
            String simulatedSecret = "pi_sim_" + UUID.randomUUID().toString().replace("-", "") + "_secret_test";
            return ResponseEntity.ok(ApiResponse.success(
                Map.of(
                    "clientSecret", simulatedSecret,
                    "mode", "simulation"
                )
            ));
        }

        Stripe.apiKey = stripeSecretKey;

        try {
            long amount = ((Number) body.getOrDefault("amount", 0)).longValue();
            String currency = (String) body.getOrDefault("currency", "usd");

            PaymentIntentCreateParams params = PaymentIntentCreateParams.builder()
                    .setAmount(amount)
                    .setCurrency(currency)
                    .setAutomaticPaymentMethods(
                        PaymentIntentCreateParams.AutomaticPaymentMethods.builder()
                            .setEnabled(true)
                            .build()
                    )
                    .build();

            PaymentIntent intent = PaymentIntent.create(params);
            return ResponseEntity.ok(ApiResponse.success(
                Map.of("clientSecret", intent.getClientSecret())
            ));

        } catch (StripeException e) {
            // Stripe hatası — simülasyon moduna düş
            String simulatedSecret = "pi_sim_" + UUID.randomUUID().toString().replace("-", "") + "_secret_test";
            return ResponseEntity.ok(ApiResponse.success(
                Map.of(
                    "clientSecret", simulatedSecret,
                    "mode", "simulation"
                )
            ));
        }
    }
}

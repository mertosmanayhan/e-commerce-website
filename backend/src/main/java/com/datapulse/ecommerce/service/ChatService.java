package com.datapulse.ecommerce.service;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.Query;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * Dynamic Query Builder — executes chatbot-generated SQL safely.
 * Only SELECT statements are allowed; DDL/DML is rejected.
 */
@Service
public class ChatService {

    @PersistenceContext
    private EntityManager em;

    private static final List<String> BLOCKED = List.of(
        "DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE", "ALTER",
        "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
    );

    /**
     * Validates and executes a raw SQL query.
     * Returns a list of rows, each row being a Map of column→value.
     */
    public Map<String, Object> executeQuery(String sql) {
        Map<String, Object> result = new LinkedHashMap<>();

        // Security validation
        String upper = sql.trim().toUpperCase();
        if (!upper.startsWith("SELECT")) {
            result.put("error", "Sadece SELECT sorguları çalıştırılabilir.");
            return result;
        }
        for (String blocked : BLOCKED) {
            if (upper.contains(blocked)) {
                result.put("error", "Güvenlik ihlali: '" + blocked + "' ifadesi kullanılamaz.");
                return result;
            }
        }

        // Execute
        try {
            Query query = em.createNativeQuery(sql);
            query.setMaxResults(500); // Limit results

            @SuppressWarnings("unchecked")
            List<Object> rows = query.getResultList();

            List<Object> data = new ArrayList<>();
            for (Object row : rows) {
                if (row instanceof Object[] arr) {
                    // Multiple columns
                    List<Object> rowList = new ArrayList<>();
                    for (Object cell : arr) rowList.add(cell);
                    data.add(rowList);
                } else {
                    // Single column
                    data.add(row);
                }
            }

            result.put("sql", sql);
            result.put("rowCount", data.size());
            result.put("rows", data);
            result.put("success", true);
        } catch (Exception e) {
            result.put("error", "SQL hatası: " + e.getMessage());
            result.put("success", false);
        }

        return result;
    }
}

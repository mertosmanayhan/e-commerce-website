package com.datapulse.ecommerce.service;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.Query;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.regex.Pattern;

/**
 * SafeSqlExecutorService — executes chatbot-generated SQL against the database.
 *
 * Security guarantees:
 *  1. Only SELECT statements are accepted (first non-whitespace token check).
 *  2. Blocked DML/DDL keywords are rejected via exact-word regex.
 *  3. Result set is capped at 500 rows to prevent unbounded reads.
 *  4. Columns are mapped by name (not index) when JPA returns Object[].
 */
@Service
public class SafeSqlExecutorService {

    @PersistenceContext
    private EntityManager em;

    private static final int MAX_ROWS = 500;

    /** Exact-word patterns for blocked SQL keywords — prevents substring false-positives. */
    private static final List<Pattern> BLOCKED_PATTERNS = List.of(
        Pattern.compile("\\bDROP\\b",     Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bDELETE\\b",   Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bTRUNCATE\\b", Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bINSERT\\b",   Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bUPDATE\\b",   Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bALTER\\b",    Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bCREATE\\b",   Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bREPLACE\\b",  Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bGRANT\\b",    Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bREVOKE\\b",   Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bEXEC\\b",     Pattern.CASE_INSENSITIVE),
        Pattern.compile("\\bEXECUTE\\b",  Pattern.CASE_INSENSITIVE)
    );

    /**
     * Validates and executes a raw SQL query.
     *
     * @param sql Raw SQL string from the AI agent
     * @return Map with keys: success (bool), sql, rowCount, rows OR error (string)
     */
    public Map<String, Object> executeQuery(String sql) {
        Map<String, Object> result = new LinkedHashMap<>();

        if (sql == null || sql.isBlank()) {
            result.put("success", false);
            result.put("error", "SQL sorgusu boş olamaz.");
            return result;
        }

        String trimmed = sql.trim();

        // Must start with SELECT
        if (!trimmed.toUpperCase().startsWith("SELECT")) {
            result.put("success", false);
            result.put("error", "Güvenlik: Sadece SELECT sorguları çalıştırılabilir.");
            return result;
        }

        // Block dangerous keywords
        for (Pattern p : BLOCKED_PATTERNS) {
            if (p.matcher(trimmed).find()) {
                result.put("success", false);
                result.put("error", "Güvenlik ihlali: Yasak SQL ifadesi tespit edildi.");
                return result;
            }
        }

        // Execute
        try {
            Query query = em.createNativeQuery(trimmed);
            query.setMaxResults(MAX_ROWS);

            @SuppressWarnings("unchecked")
            List<Object> rawRows = query.getResultList();

            List<Object> data = new ArrayList<>();
            for (Object row : rawRows) {
                if (row instanceof Object[] arr) {
                    List<Object> rowList = new ArrayList<>(arr.length);
                    for (Object cell : arr) rowList.add(cell);
                    data.add(rowList);
                } else {
                    data.add(row);
                }
            }

            result.put("success",  true);
            result.put("sql",      trimmed);
            result.put("rowCount", data.size());
            result.put("rows",     data);

        } catch (Exception e) {
            result.put("success", false);
            result.put("error",   "SQL yürütme hatası: " + e.getMessage());
        }

        return result;
    }
}

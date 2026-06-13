package com.example.auth.util;

import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class JwtUtilTest {

    private JwtUtil jwtUtil;

    @BeforeEach
    void setUp() {
        jwtUtil = new JwtUtil();
        jwtUtil.setSecret("test-secret-key-for-unit-testing-must-be-long-enough");
        jwtUtil.setExpiration(86400000L);
    }

    @Test
    void generateToken_shouldReturnValidJwt() {
        String token = jwtUtil.generateToken("user-123", "13800138000");

        assertNotNull(token);
        assertTrue(token.split("\\.").length == 3);
    }

    @Test
    void parseToken_shouldReturnCorrectClaims() {
        String token = jwtUtil.generateToken("user-123", "13800138000");

        Claims claims = jwtUtil.parseToken(token);

        assertEquals("user-123", claims.get("userId", String.class));
        assertEquals("13800138000", claims.get("phone", String.class));
    }

    @Test
    void parseToken_invalidToken_shouldThrowException() {
        assertThrows(Exception.class, () -> jwtUtil.parseToken("invalid.token.here"));
    }
}

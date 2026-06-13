package com.example.auth.service;

import com.example.auth.model.CodeEntry;
import com.example.auth.util.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import static org.junit.jupiter.api.Assertions.*;

class AuthServiceTest {

    private AuthService authService;

    @BeforeEach
    void setUp() {
        JwtUtil jwtUtil = new JwtUtil();
        jwtUtil.setSecret("test-secret-key-for-unit-testing-must-be-long-enough");
        jwtUtil.setExpiration(86400000L);

        authService = new AuthService(jwtUtil);
    }

    // ===== sendCode 测试 =====

    @Test
    void sendCode_firstRequest_shouldSucceed() {
        assertDoesNotThrow(() -> authService.sendCode("13800138000"));
    }

    @Test
    void sendCode_samePhoneWithin60Seconds_shouldThrow() {
        authService.sendCode("13800138000");

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> authService.sendCode("13800138000"));
        assertEquals("发送验证码太频繁，请稍后再试", ex.getMessage());
    }

    // ===== login 测试 =====

    @Test
    void login_validCode_shouldReturnTokenAndNewUser() {
        authService.sendCode("13800138000");
        String code = authService.getCodeForPhone("13800138000");

        Map<String, Object> result = authService.login("13800138000", code);

        assertNotNull(result.get("token"));
        assertEquals(true, result.get("isNewUser"));
    }

    @Test
    void login_noCodeSent_shouldThrow() {
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> authService.login("13800138000", "123456"));
        assertEquals("验证码无效，请先获取验证码", ex.getMessage());
    }

    @Test
    void login_wrongCode_shouldThrow() {
        authService.sendCode("13800138000");

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> authService.login("13800138000", "000000"));
        assertEquals("验证码错误", ex.getMessage());
    }

    @Test
    void login_existingUser_shouldReturnIsNewUserFalse() {
        authService.sendCode("13800138000");
        String code = authService.getCodeForPhone("13800138000");
        authService.login("13800138000", code);

        authService.sendCode("13800138000");
        String code2 = authService.getCodeForPhone("13800138000");
        Map<String, Object> result = authService.login("13800138000", code2);

        assertEquals(false, result.get("isNewUser"));
    }

    @Test
    void login_codeUsedTwice_shouldThrow() {
        authService.sendCode("13800138000");
        String code = authService.getCodeForPhone("13800138000");
        authService.login("13800138000", code);

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> authService.login("13800138000", code));
        assertEquals("验证码无效，请先获取验证码", ex.getMessage());
    }

    @Test
    void login_expiredCode_shouldThrow() throws Exception {
        authService.sendCode("13800138000");
        String code = authService.getCodeForPhone("13800138000");

        // 通过反射获取 codeMap，将验证码设置为已过期
        Field codeMapField = AuthService.class.getDeclaredField("codeMap");
        codeMapField.setAccessible(true);
        @SuppressWarnings("unchecked")
        ConcurrentHashMap<String, CodeEntry> codeMap =
                (ConcurrentHashMap<String, CodeEntry>) codeMapField.get(authService);
        codeMap.put("13800138000", new CodeEntry(code,
                LocalDateTime.now().minusMinutes(10),
                LocalDateTime.now().minusMinutes(5)));

        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> authService.login("13800138000", code));
        assertEquals("验证码已过期，请重新获取", ex.getMessage());
    }

    @Test
    void login_maxAttemptsExceeded_shouldInvalidateCode() {
        authService.sendCode("13800138000");

        // 连续错误 4 次仍返回"验证码错误"
        for (int i = 0; i < 4; i++) {
            RuntimeException ex = assertThrows(RuntimeException.class,
                    () -> authService.login("13800138000", "000000"));
            assertEquals("验证码错误", ex.getMessage());
        }

        // 第 5 次错误：验证码被删除，返回"错误次数过多"
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> authService.login("13800138000", "000000"));
        assertEquals("验证码错误次数过多，请重新获取验证码", ex.getMessage());

        // 再次登录应返回"验证码无效"（已被删除）
        RuntimeException ex2 = assertThrows(RuntimeException.class,
                () -> authService.login("13800138000", "000000"));
        assertEquals("验证码无效，请先获取验证码", ex2.getMessage());
    }
}

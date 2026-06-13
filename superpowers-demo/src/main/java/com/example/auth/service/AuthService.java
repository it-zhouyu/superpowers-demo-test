package com.example.auth.service;

import com.example.auth.model.CodeEntry;
import com.example.auth.model.User;
import com.example.auth.util.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AuthService {

    private static final long CODE_EXPIRE_MINUTES = 5;
    private static final long CODE_COOLDOWN_SECONDS = 60;
    private static final int MAX_LOGIN_ATTEMPTS = 5;
    private static final Random RANDOM = new Random();

    private final ConcurrentHashMap<String, CodeEntry> codeMap = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, User> userMap = new ConcurrentHashMap<>();
    private final SmsService smsService;
    private final JwtUtil jwtUtil;

    public AuthService(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
        this.smsService = new SmsService() {
            @Override
            public void sendCode(String phone, String code) {
            }
        };
    }

    @Autowired
    public AuthService(SmsService smsService, JwtUtil jwtUtil) {
        this.smsService = smsService;
        this.jwtUtil = jwtUtil;
    }

    public void sendCode(String phone) {
        LocalDateTime now = LocalDateTime.now();

        CodeEntry existing = codeMap.get(phone);
        if (existing != null) {
            Duration elapsed = Duration.between(existing.getCreateTime(), now);
            if (elapsed.getSeconds() < CODE_COOLDOWN_SECONDS) {
                throw new RuntimeException("发送验证码太频繁，请稍后再试");
            }
        }

        String code = generateCode();
        LocalDateTime expireTime = now.plusMinutes(CODE_EXPIRE_MINUTES);
        codeMap.put(phone, new CodeEntry(code, now, expireTime));

        smsService.sendCode(phone, code);
    }

    public Map<String, Object> login(String phone, String inputCode) {
        CodeEntry entry = codeMap.get(phone);
        if (entry == null) {
            throw new RuntimeException("验证码无效，请先获取验证码");
        }

        if (LocalDateTime.now().isAfter(entry.getExpireTime())) {
            codeMap.remove(phone);
            throw new RuntimeException("验证码已过期，请重新获取");
        }

        if (!entry.getCode().equals(inputCode)) {
            entry.incrementAttemptCount();
            if (entry.getAttemptCount() >= MAX_LOGIN_ATTEMPTS) {
                codeMap.remove(phone);
                throw new RuntimeException("验证码错误次数过多，请重新获取验证码");
            }
            throw new RuntimeException("验证码错误");
        }

        codeMap.remove(phone);

        boolean isNewUser = !userMap.containsKey(phone);
        User user;
        if (isNewUser) {
            user = User.create(phone);
            userMap.put(phone, user);
        } else {
            user = userMap.get(phone);
        }

        String token = jwtUtil.generateToken(user.getId(), user.getPhone());

        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("isNewUser", isNewUser);
        return result;
    }

    /**
     * 测试辅助方法：获取指定手机号的验证码明文
     * 仅用于测试，生产代码不应调用此方法
     */
    public String getCodeForPhone(String phone) {
        CodeEntry entry = codeMap.get(phone);
        return entry != null ? entry.getCode() : null;
    }

    private String generateCode() {
        int code = 100000 + RANDOM.nextInt(900000);
        return String.valueOf(code);
    }
}

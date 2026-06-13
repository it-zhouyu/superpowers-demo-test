# 手机号验证码登录注册 API 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现基于手机号 + 验证码的登录注册合一 API，包含发送验证码和登录注册两个接口

**Architecture:** Spring Boot 3.2 单体应用，ConcurrentHashMap 内存存储，Mock 短信服务，JWT 无状态认证。Controller → Service 两层架构，全局异常处理统一响应格式

**Tech Stack:** Java 17, Spring Boot 3.2.5, Maven, JJWT 0.12.5, Jakarta Validation, JUnit 5, MockMvc

---

## File Structure

| File | Responsibility |
|------|---------------|
| `pom.xml` | Maven 项目配置，依赖管理 |
| `src/main/resources/application.yml` | 服务端口、JWT 密钥和过期时间 |
| `src/main/java/com/example/auth/AuthApplication.java` | Spring Boot 启动类 |
| `src/main/java/com/example/auth/common/Result.java` | 统一响应体 `{code, message, data}` |
| `src/main/java/com/example/auth/model/User.java` | 用户实体 `id, phone, createTime` |
| `src/main/java/com/example/auth/model/SendCodeRequest.java` | 发送验证码请求 DTO |
| `src/main/java/com/example/auth/model/LoginRequest.java` | 登录请求 DTO |
| `src/main/java/com/example/auth/model/CodeEntry.java` | 验证码记录 `code, createTime, expireTime` |
| `src/main/java/com/example/auth/util/JwtUtil.java` | JWT 生成与解析 |
| `src/main/java/com/example/auth/service/SmsService.java` | 短信发送接口 |
| `src/main/java/com/example/auth/service/impl/MockSmsServiceImpl.java` | Mock 短信实现 |
| `src/main/java/com/example/auth/service/AuthService.java` | 核心业务逻辑（验证码管理 + 用户管理） |
| `src/main/java/com/example/auth/controller/AuthController.java` | 认证接口（2 个端点） |
| `src/main/java/com/example/auth/controller/GlobalExceptionHandler.java` | 全局异常处理 |
| `src/test/java/com/example/auth/util/JwtUtilTest.java` | JwtUtil 单元测试 |
| `src/test/java/com/example/auth/service/AuthServiceTest.java` | AuthService 单元测试 |
| `src/test/java/com/example/auth/controller/AuthControllerTest.java` | 接口集成测试 |

---

### Task 1: 项目脚手架

**Files:**
- Create: `pom.xml`
- Create: `src/main/resources/application.yml`
- Create: `src/main/java/com/example/auth/AuthApplication.java`

- [ ] **Step 1: 创建 pom.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.5</version>
        <relativePath/>
    </parent>

    <groupId>com.example</groupId>
    <artifactId>phone-auth-api</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>phone-auth-api</name>
    <description>手机号验证码登录注册 API</description>

    <properties>
        <java.version>17</java.version>
        <jjwt.version>0.12.5</jjwt.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>${jjwt.version}</version>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-impl</artifactId>
            <version>${jjwt.version}</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-jackson</artifactId>
            <version>${jjwt.version}</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 2: 创建 application.yml**

```yaml
server:
  port: 8080

jwt:
  secret: my-demo-secret-key-for-phone-auth-api-2024-please-replace-in-production
  expiration: 86400000
```

- [ ] **Step 3: 创建 AuthApplication.java**

```java
package com.example.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(AuthApplication.class, args);
    }
}
```

- [ ] **Step 4: 验证项目能编译启动**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add pom.xml src/main/resources/application.yml src/main/java/com/example/auth/AuthApplication.java
git commit -m "feat: 初始化 Spring Boot 项目脚手架"
```

---

### Task 2: 统一响应体和基础模型

**Files:**
- Create: `src/main/java/com/example/auth/common/Result.java`
- Create: `src/main/java/com/example/auth/model/CodeEntry.java`
- Create: `src/main/java/com/example/auth/model/User.java`

- [ ] **Step 1: 创建 Result.java**

```java
package com.example.auth.common;

public class Result<T> {

    private int code;
    private String message;
    private T data;

    public Result() {
    }

    public Result(int code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(200, "success", data);
    }

    public static <T> Result<T> success(String message, T data) {
        return new Result<>(200, message, data);
    }

    public static <T> Result<T> error(int code, String message) {
        return new Result<>(code, message, null);
    }

    public int getCode() {
        return code;
    }

    public void setCode(int code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }
}
```

- [ ] **Step 2: 创建 CodeEntry.java**

```java
package com.example.auth.model;

import java.time.LocalDateTime;

public class CodeEntry {

    private String code;
    private LocalDateTime createTime;
    private LocalDateTime expireTime;

    public CodeEntry(String code, LocalDateTime createTime, LocalDateTime expireTime) {
        this.code = code;
        this.createTime = createTime;
        this.expireTime = expireTime;
    }

    public String getCode() {
        return code;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public LocalDateTime getExpireTime() {
        return expireTime;
    }
}
```

- [ ] **Step 3: 创建 User.java**

```java
package com.example.auth.model;

import java.time.LocalDateTime;
import java.util.UUID;

public class User {

    private String id;
    private String phone;
    private LocalDateTime createTime;

    public User() {
    }

    public static User create(String phone) {
        User user = new User();
        user.id = UUID.randomUUID().toString();
        user.phone = phone;
        user.createTime = LocalDateTime.now();
        return user;
    }

    public String getId() {
        return id;
    }

    public String getPhone() {
        return phone;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }
}
```

- [ ] **Step 4: 验证编译**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/common/Result.java src/main/java/com/example/auth/model/CodeEntry.java src/main/java/com/example/auth/model/User.java
git commit -m "feat: 添加统一响应体 Result 和基础模型 User、CodeEntry"
```

---

### Task 3: 请求 DTO

**Files:**
- Create: `src/main/java/com/example/auth/model/SendCodeRequest.java`
- Create: `src/main/java/com/example/auth/model/LoginRequest.java`

- [ ] **Step 1: 创建 SendCodeRequest.java**

```java
package com.example.auth.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public class SendCodeRequest {

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }
}
```

- [ ] **Step 2: 创建 LoginRequest.java**

```java
package com.example.auth.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public class LoginRequest {

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    @NotBlank(message = "验证码不能为空")
    @Pattern(regexp = "^\\d{6}$", message = "验证码必须是6位数字")
    private String code;

    public String getPhone() {
        return phone;
    }

    public void setPhone(String phone) {
        this.phone = phone;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }
}
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/example/auth/model/SendCodeRequest.java src/main/java/com/example/auth/model/LoginRequest.java
git commit -m "feat: 添加 SendCodeRequest 和 LoginRequest 请求 DTO"
```

---

### Task 4: JwtUtil 工具类及测试

**Files:**
- Create: `src/main/java/com/example/auth/util/JwtUtil.java`
- Create: `src/test/java/com/example/auth/util/JwtUtilTest.java`

- [ ] **Step 1: 编写 JwtUtilTest 失败测试**

```java
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -pl . -Dtest=JwtUtilTest -q 2>&1 | tail -5`
Expected: 编译失败（JwtUtil 类不存在）

- [ ] **Step 3: 实现 JwtUtil.java**

```java
package com.example.auth.util;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration}")
    private Long expiration;

    public void setSecret(String secret) {
        this.secret = secret;
    }

    public void setExpiration(Long expiration) {
        this.expiration = expiration;
    }

    public String generateToken(String userId, String phone) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expiration);

        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));

        return Jwts.builder()
                .subject(userId)
                .claim("userId", userId)
                .claim("phone", phone)
                .issuedAt(now)
                .expiration(expiryDate)
                .signWith(key)
                .compact();
    }

    public Claims parseToken(String token) {
        SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));

        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -Dtest=JwtUtilTest -q 2>&1 | tail -5`
Expected: Tests run: 3, Failures: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/util/JwtUtil.java src/test/java/com/example/auth/util/JwtUtilTest.java
git commit -m "feat: 添加 JwtUtil 工具类及单元测试"
```

---

### Task 5: SmsService 接口和 Mock 实现

**Files:**
- Create: `src/main/java/com/example/auth/service/SmsService.java`
- Create: `src/main/java/com/example/auth/service/impl/MockSmsServiceImpl.java`

- [ ] **Step 1: 创建 SmsService 接口**

```java
package com.example.auth.service;

public interface SmsService {

    void sendCode(String phone, String code);
}
```

- [ ] **Step 2: 创建 MockSmsServiceImpl**

```java
package com.example.auth.service.impl;

import com.example.auth.service.SmsService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class MockSmsServiceImpl implements SmsService {

    private static final Logger log = LoggerFactory.getLogger(MockSmsServiceImpl.class);

    @Override
    public void sendCode(String phone, String code) {
        log.info("[Mock SMS] 向 {} 发送验证码: {}", phone, code);
    }
}
```

- [ ] **Step 3: 验证编译**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/example/auth/service/SmsService.java src/main/java/com/example/auth/service/impl/MockSmsServiceImpl.java
git commit -m "feat: 添加 SmsService 接口和 Mock 实现"
```

---

### Task 6: AuthService 核心业务及测试

**Files:**
- Create: `src/main/java/com/example/auth/service/AuthService.java`
- Create: `src/test/java/com/example/auth/service/AuthServiceTest.java`

- [ ] **Step 1: 编写 AuthServiceTest 失败测试**

```java
package com.example.auth.service;

import com.example.auth.util.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

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
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -Dtest=AuthServiceTest -q 2>&1 | tail -5`
Expected: 编译失败（AuthService 类不存在）

- [ ] **Step 3: 实现 AuthService.java**

```java
package com.example.auth.service;

import com.example.auth.model.CodeEntry;
import com.example.auth.model.User;
import com.example.auth.util.JwtUtil;
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -Dtest=AuthServiceTest -q 2>&1 | tail -5`
Expected: Tests run: 6, Failures: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/service/AuthService.java src/test/java/com/example/auth/service/AuthServiceTest.java
git commit -m "feat: 添加 AuthService 核心业务逻辑及单元测试"
```

---

### Task 7: GlobalExceptionHandler

**Files:**
- Create: `src/main/java/com/example/auth/controller/GlobalExceptionHandler.java`

- [ ] **Step 1: 创建 GlobalExceptionHandler.java**

```java
package com.example.auth.controller;

import com.example.auth.common.Result;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleValidationException(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getDefaultMessage())
                .findFirst()
                .orElse("参数校验失败");
        return Result.error(400, message);
    }

    @ExceptionHandler(RuntimeException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleRuntimeException(RuntimeException ex) {
        return Result.error(400, ex.getMessage());
    }

    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public Result<Void> handleException(Exception ex) {
        return Result.error(500, "服务器内部错误");
    }
}
```

- [ ] **Step 2: 验证编译**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 3: Commit**

```bash
git add src/main/java/com/example/auth/controller/GlobalExceptionHandler.java
git commit -m "feat: 添加全局异常处理器"
```

---

### Task 8: AuthController 及集成测试

**Files:**
- Create: `src/main/java/com/example/auth/controller/AuthController.java`
- Create: `src/test/java/com/example/auth/controller/AuthControllerTest.java`

- [ ] **Step 1: 编写 AuthControllerTest 失败测试**

```java
package com.example.auth.controller;

import com.example.auth.service.AuthService;
import com.example.auth.util.JwtUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.bean.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.HashMap;
import java.util.Map;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(AuthController.class)
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private AuthService authService;

    @MockBean
    private JwtUtil jwtUtil;

    @Autowired
    private ObjectMapper objectMapper;

    // ===== send-code 测试 =====

    @Test
    void sendCode_validPhone_shouldReturn200() throws Exception {
        doNothing().when(authService).sendCode("13800138000");

        mockMvc.perform(post("/api/auth/send-code")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13800138000\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("验证码发送成功"));
    }

    @Test
    void sendCode_emptyPhone_shouldReturn400() throws Exception {
        mockMvc.perform(post("/api/auth/send-code")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    void sendCode_invalidPhone_shouldReturn400() throws Exception {
        mockMvc.perform(post("/api/auth/send-code")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"123\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    void sendCode_tooFrequent_shouldReturn400() throws Exception {
        doThrow(new RuntimeException("发送验证码太频繁，请稍后再试"))
                .when(authService).sendCode("13800138000");

        mockMvc.perform(post("/api/auth/send-code")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13800138000\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("发送验证码太频繁，请稍后再试"));
    }

    // ===== login 测试 =====

    @Test
    void login_validRequest_shouldReturnToken() throws Exception {
        Map<String, Object> loginResult = new HashMap<>();
        loginResult.put("token", "test-jwt-token");
        loginResult.put("isNewUser", true);

        when(authService.login("13800138000", "123456")).thenReturn(loginResult);

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13800138000\",\"code\":\"123456\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("登录成功"))
                .andExpect(jsonPath("$.data.token").value("test-jwt-token"))
                .andExpect(jsonPath("$.data.isNewUser").value(true));
    }

    @Test
    void login_emptyCode_shouldReturn400() throws Exception {
        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13800138000\",\"code\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400));
    }

    @Test
    void login_invalidCode_shouldReturn400() throws Exception {
        when(authService.login("13800138000", "123456"))
                .thenThrow(new RuntimeException("验证码错误"));

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13800138000\",\"code\":\"123456\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("验证码错误"));
    }
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -Dtest=AuthControllerTest -q 2>&1 | tail -5`
Expected: 编译失败（AuthController 类不存在）

- [ ] **Step 3: 实现 AuthController.java**

```java
package com.example.auth.controller;

import com.example.auth.common.Result;
import com.example.auth.model.LoginRequest;
import com.example.auth.model.SendCodeRequest;
import com.example.auth.service.AuthService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/send-code")
    public Result<Void> sendCode(@Valid @RequestBody SendCodeRequest request) {
        authService.sendCode(request.getPhone());
        return Result.success("验证码发送成功", null);
    }

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@Valid @RequestBody LoginRequest request) {
        Map<String, Object> data = authService.login(request.getPhone(), request.getCode());
        return Result.success("登录成功", data);
    }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -Dtest=AuthControllerTest -q 2>&1 | tail -5`
Expected: Tests run: 7, Failures: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/controller/AuthController.java src/test/java/com/example/auth/controller/AuthControllerTest.java
git commit -m "feat: 添加 AuthController 和集成测试"
```

---

### Task 9: 全量验证

**Files:** 无新增

- [ ] **Step 1: 运行全部测试**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn test -q 2>&1 | tail -10`
Expected: Tests run: 16, Failures: 0, Errors: 0

- [ ] **Step 2: 启动应用并手动测试**

Run: `cd /Users/dadudu/idea/vibe-coding-vip/superpowers-demo && mvn spring-boot:run -q`

在另一个终端执行：

```bash
# 测试发送验证码
curl -s -X POST http://localhost:8080/api/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000"}'

# 查看控制台日志获取验证码，然后用实际验证码替换 123456
curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","code":"123456"}'
```

Expected:
- 发送验证码返回 `{"code":200,"message":"验证码发送成功","data":null}`
- 控制台日志打印 `[Mock SMS] 向 13800138000 发送验证码: XXXXXX`
- 登录返回 `{"code":200,"message":"登录成功","data":{"token":"eyJ...","isNewUser":true}}`

- [ ] **Step 3: 测试异常场景**

```bash
# 空手机号
curl -s -X POST http://localhost:8080/api/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":""}'

# 重复发送
curl -s -X POST http://localhost:8080/api/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000"}'
curl -s -X POST http://localhost:8080/api/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000"}'

# 未发送验证码直接登录
curl -s -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13900139000","code":"123456"}'
```

Expected:
- 空手机号返回 400 + `"手机号不能为空"`
- 重复发送返回 400 + `"发送验证码太频繁，请稍后再试"`
- 未发验证码直接登录返回 400 + `"验证码无效，请先获取验证码"`

- [ ] **Step 4: 最终 Commit**

```bash
git add -A
git commit -m "feat: 手机号验证码登录注册 API 全部功能完成"
```

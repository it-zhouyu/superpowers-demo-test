# 手机号验证码登录注册 API 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现手机号 + 验证码的登录注册一体化 API，包含发送验证码和验证码登录两个端点。

**Architecture:** 单模块 Spring Boot 应用，按包分层（controller / service / model / common / util）。短信服务抽象为接口便于后续切换，数据存储使用 ConcurrentHashMap 纯内存方案，认证使用 JWT。

**Tech Stack:** Java 17, Spring Boot 3.2.x, Maven, JJWT (JWT 库), Spring Boot Starter Validation

---

## File Structure

| 文件 | 职责 |
|------|------|
| `pom.xml` | Maven 依赖配置 |
| `src/main/resources/application.yml` | 应用配置（端口、JWT 密钥等） |
| `src/.../AuthApplication.java` | Spring Boot 启动类 |
| `src/.../common/Result.java` | 统一响应包装类 |
| `src/.../model/User.java` | 用户实体 |
| `src/.../model/SendCodeRequest.java` | 发送验证码请求 DTO |
| `src/.../model/LoginRequest.java` | 登录请求 DTO |
| `src/.../model/CodeEntry.java` | 验证码存储实体 |
| `src/.../util/JwtUtil.java` | JWT 生成与解析工具类 |
| `src/.../service/SmsService.java` | 短信服务接口 |
| `src/.../service/impl/MockSmsServiceImpl.java` | Mock 短信实现 |
| `src/.../service/AuthService.java` | 认证业务逻辑 |
| `src/.../controller/AuthController.java` | API 端点控制器 |
| `src/.../controller/GlobalExceptionHandler.java` | 全局异常处理 |
| `src/test/.../util/JwtUtilTest.java` | JWT 工具类单元测试 |
| `src/test/.../service/AuthServiceTest.java` | 认证服务单元测试 |
| `src/test/.../controller/AuthControllerTest.java` | 控制器集成测试 |

基础包路径：`com.example.auth`

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
    <artifactId>phone-auth-demo</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>phone-auth-demo</name>
    <description>Phone verification code login/register API</description>

    <properties>
        <java.version>17</java.version>
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
            <version>0.12.5</version>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-impl</artifactId>
            <version>0.12.5</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-jackson</artifactId>
            <version>0.12.5</version>
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

- [ ] **Step 3: 创建启动类**

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

Run: `cd superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add pom.xml src/
git commit -m "feat: 项目脚手架 — Spring Boot 3.2 + Java 17 + Maven"
```

---

### Task 2: 公共类（Result + CodeEntry + GlobalExceptionHandler）

**Files:**
- Create: `src/main/java/com/example/auth/common/Result.java`
- Create: `src/main/java/com/example/auth/model/CodeEntry.java`
- Create: `src/main/java/com/example/auth/controller/GlobalExceptionHandler.java`

- [ ] **Step 1: 创建统一响应包装类 Result**

```java
package com.example.auth.common;

public class Result<T> {
    private int code;
    private String message;
    private T data;

    public static <T> Result<T> success(String message) {
        Result<T> r = new Result<>();
        r.code = 200;
        r.message = message;
        return r;
    }

    public static <T> Result<T> success(String message, T data) {
        Result<T> r = new Result<>();
        r.code = 200;
        r.message = message;
        r.data = data;
        return r;
    }

    public static <T> Result<T> error(int code, String message) {
        Result<T> r = new Result<>();
        r.code = code;
        r.message = message;
        return r;
    }

    public int getCode() { return code; }
    public void setCode(int code) { this.code = code; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public T getData() { return data; }
    public void setData(T data) { this.data = data; }
}
```

- [ ] **Step 2: 创建 CodeEntry**

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

    public String getCode() { return code; }
    public LocalDateTime getCreateTime() { return createTime; }
    public LocalDateTime getExpireTime() { return expireTime; }
    public boolean isExpired() {
        return LocalDateTime.now().isAfter(expireTime);
    }
}
```

- [ ] **Step 3: 创建全局异常处理器**

```java
package com.example.auth.controller;

import com.example.auth.common.Result;
import org.springframework.http.HttpStatus;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleValidation(MethodArgumentNotValidException ex) {
        FieldError fe = ex.getBindingResult().getFieldError();
        String msg = fe != null ? fe.getField() + ": " + fe.getDefaultMessage() : "参数校验失败";
        return Result.error(400, msg);
    }

    @ExceptionHandler(RuntimeException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public Result<Void> handleRuntime(RuntimeException ex) {
        return Result.error(400, ex.getMessage());
    }
}
```

- [ ] **Step 4: 编译验证**

Run: `cd superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/common/Result.java src/main/java/com/example/auth/model/CodeEntry.java src/main/java/com/example/auth/controller/GlobalExceptionHandler.java
git commit -m "feat: 添加统一响应类、验证码实体、全局异常处理器"
```

---

### Task 3: 数据模型（User + DTO）

**Files:**
- Create: `src/main/java/com/example/auth/model/User.java`
- Create: `src/main/java/com/example/auth/model/SendCodeRequest.java`
- Create: `src/main/java/com/example/auth/model/LoginRequest.java`

- [ ] **Step 1: 创建 User 实体**

```java
package com.example.auth.model;

import java.time.LocalDateTime;
import java.util.concurrent.atomic.AtomicLong;

public class User {
    private static final AtomicLong ID_GENERATOR = new AtomicLong(1);

    private Long id;
    private String phone;
    private LocalDateTime createTime;

    public User(String phone) {
        this.id = ID_GENERATOR.getAndIncrement();
        this.phone = phone;
        this.createTime = LocalDateTime.now();
    }

    public Long getId() { return id; }
    public String getPhone() { return phone; }
    public LocalDateTime getCreateTime() { return createTime; }
}
```

- [ ] **Step 2: 创建 SendCodeRequest DTO**

```java
package com.example.auth.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public class SendCodeRequest {

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
}
```

- [ ] **Step 3: 创建 LoginRequest DTO**

```java
package com.example.auth.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public class LoginRequest {

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String phone;

    @NotBlank(message = "验证码不能为空")
    @Size(min = 6, max = 6, message = "验证码必须是6位数字")
    private String code;

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }
    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }
}
```

- [ ] **Step 4: 编译验证**

Run: `cd superpowers-demo && mvn compile -q`
Expected: BUILD SUCCESS

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/model/User.java src/main/java/com/example/auth/model/SendCodeRequest.java src/main/java/com/example/auth/model/LoginRequest.java
git commit -m "feat: 添加 User 实体和请求 DTO"
```

---

### Task 4: JwtUtil + 单元测试

**Files:**
- Create: `src/main/java/com/example/auth/util/JwtUtil.java`
- Create: `src/test/java/com/example/auth/util/JwtUtilTest.java`

- [ ] **Step 1: 写 JwtUtil 的失败测试**

```java
package com.example.auth.util;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class JwtUtilTest {

    private final JwtUtil jwtUtil = new JwtUtil();

    @Test
    void generateToken_shouldReturnValidToken() {
        String token = jwtUtil.generateToken(1L, "13800138000");
        assertNotNull(token);
        assertFalse(token.isEmpty());
    }

    @Test
    void parseToken_shouldReturnCorrectClaims() {
        String token = jwtUtil.generateToken(1L, "13800138000");
        assertEquals(1L, jwtUtil.getUserId(token));
        assertEquals("13800138000", jwtUtil.getPhone(token));
    }

    @Test
    void parseToken_invalidToken_shouldThrow() {
        assertThrows(Exception.class, () -> jwtUtil.getUserId("invalid.token.here"));
    }
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd superpowers-demo && mvn test -pl . -Dtest=JwtUtilTest -q 2>&1 | tail -5`
Expected: 编译失败或测试失败（JwtUtil 类不存在）

- [ ] **Step 3: 实现 JwtUtil**

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
    private long expiration;

    private SecretKey getKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String generateToken(Long userId, String phone) {
        Date now = new Date();
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("phone", phone)
                .issuedAt(now)
                .expiration(new Date(now.getTime() + expiration))
                .signWith(getKey())
                .compact();
    }

    private Claims parseClaims(String token) {
        return Jwts.parser()
                .verifyWith(getKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    public Long getUserId(String token) {
        return Long.parseLong(parseClaims(token).getSubject());
    }

    public String getPhone(String token) {
        return parseClaims(token).get("phone", String.class);
    }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd superpowers-demo && mvn test -Dtest=JwtUtilTest -q`
Expected: Tests run: 3, Failures: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/util/JwtUtil.java src/test/java/com/example/auth/util/JwtUtilTest.java
git commit -m "feat: 添加 JwtUtil 及单元测试"
```

---

### Task 5: SmsService 接口 + Mock 实现 + 测试

**Files:**
- Create: `src/main/java/com/example/auth/service/SmsService.java`
- Create: `src/main/java/com/example/auth/service/impl/MockSmsServiceImpl.java`
- Create: `src/test/java/com/example/auth/service/impl/MockSmsServiceImplTest.java`

- [ ] **Step 1: 写 MockSmsServiceImpl 的测试**

```java
package com.example.auth.service.impl;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class MockSmsServiceImplTest {

    private final MockSmsServiceImpl smsService = new MockSmsServiceImpl();

    @Test
    void sendCode_shouldNotThrow() {
        assertDoesNotThrow(() -> smsService.sendCode("13800138000", "123456"));
    }
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd superpowers-demo && mvn test -Dtest=MockSmsServiceImplTest -q 2>&1 | tail -5`
Expected: 编译失败（MockSmsServiceImpl 类不存在）

- [ ] **Step 3: 实现 SmsService 接口和 MockSmsServiceImpl**

SmsService 接口：

```java
package com.example.auth.service;

public interface SmsService {
    void sendCode(String phone, String code);
}
```

MockSmsServiceImpl：

```java
package com.example.auth.service.impl;

import com.example.auth.service.SmsService;
import lombok.extern.java.Log;
import org.springframework.stereotype.Service;

@Service
public class MockSmsServiceImpl implements SmsService {

    @Override
    public void sendCode(String phone, String code) {
        System.out.println("=== Mock SMS === 手机号: " + phone + ", 验证码: " + code + " ===");
    }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd superpowers-demo && mvn test -Dtest=MockSmsServiceImplTest -q`
Expected: Tests run: 1, Failures: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/service/SmsService.java src/main/java/com/example/auth/service/impl/MockSmsServiceImpl.java src/test/java/com/example/auth/service/impl/MockSmsServiceImplTest.java
git commit -m "feat: 添加 SmsService 接口及 Mock 实现"
```

---

### Task 6: AuthService + 单元测试

**Files:**
- Create: `src/main/java/com/example/auth/service/AuthService.java`
- Create: `src/test/java/com/example/auth/service/AuthServiceTest.java`

- [ ] **Step 1: 写 AuthService 的失败测试**

```java
package com.example.auth.service;

import com.example.auth.util.JwtUtil;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class AuthServiceTest {

    private AuthService authService;
    private JwtUtil jwtUtil;

    @BeforeEach
    void setUp() {
        jwtUtil = mock(JwtUtil.class);
        when(jwtUtil.generateToken(anyLong(), anyString())).thenReturn("mock-token");
        authService = new AuthService(jwtUtil);
    }

    @Test
    void sendCode_newPhone_shouldSuccess() {
        assertDoesNotThrow(() -> authService.sendCode("13800138000"));
    }

    @Test
    void sendCode_samePhoneWithin60s_shouldThrow() {
        authService.sendCode("13800138000");
        assertThrows(RuntimeException.class, () -> authService.sendCode("13800138000"));
    }

    @Test
    void login_correctCode_shouldReturnToken() {
        authService.sendCode("13800138000");
        Map<String, Object> result = authService.login("13800138000", fetchCodeFromConsole());
        assertEquals("mock-token", result.get("token"));
    }

    @Test
    void login_wrongCode_shouldThrow() {
        authService.sendCode("13800138000");
        assertThrows(RuntimeException.class, () -> authService.login("13800138000", "000000"));
    }

    @Test
    void login_expiredCode_shouldThrow() {
        authService.sendCode("13800138000");
        assertThrows(RuntimeException.class, () -> authService.login("13900139000", "123456"));
    }

    @Test
    void login_newUser_shouldSetIsNewUserTrue() {
        authService.sendCode("13800138000");
        Map<String, Object> result = authService.login("13800138000", fetchCodeFromConsole());
        assertEquals(true, result.get("isNewUser"));
    }

    @Test
    void login_existingUser_shouldSetIsNewUserFalse() {
        authService.sendCode("13800138000");
        authService.login("13800138000", fetchCodeFromConsole());

        authService.sendCode("13800138000");
        Map<String, Object> result = authService.login("13800138000", fetchCodeFromConsole());
        assertEquals(false, result.get("isNewUser"));
    }

    private String fetchCodeFromConsole() {
        return authService.getCodeForTest("13800138000");
    }
}
```

注意：测试中通过 `getCodeForTest` 方法获取实际生成的验证码来验证登录流程，该方法仅在测试中使用。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd superpowers-demo && mvn test -Dtest=AuthServiceTest -q 2>&1 | tail -5`
Expected: 编译失败（AuthService 类不存在）

- [ ] **Step 3: 实现 AuthService**

```java
package com.example.auth.service;

import com.example.auth.model.CodeEntry;
import com.example.auth.model.User;
import com.example.auth.util.JwtUtil;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class AuthService {

    private static final long CODE_EXPIRE_SECONDS = 300;
    private static final long CODE_COOLDOWN_SECONDS = 60;

    private final ConcurrentHashMap<String, CodeEntry> codeStore = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, User> userStore = new ConcurrentHashMap<>();
    private final JwtUtil jwtUtil;

    public AuthService(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    public void sendCode(String phone) {
        CodeEntry existing = codeStore.get(phone);
        if (existing != null && !existing.isExpired()
                && existing.getCreateTime().plusSeconds(CODE_COOLDOWN_SECONDS).isAfter(LocalDateTime.now())) {
            throw new RuntimeException("发送太频繁，请稍后再试");
        }

        String code = String.valueOf((int) ((Math.random() * 9 + 1) * 100000));
        LocalDateTime now = LocalDateTime.now();
        CodeEntry entry = new CodeEntry(code, now, now.plusSeconds(CODE_EXPIRE_SECONDS));
        codeStore.put(phone, entry);

        System.out.println("=== Mock SMS === 手机号: " + phone + ", 验证码: " + code + " ===");
    }

    public Map<String, Object> login(String phone, String code) {
        CodeEntry entry = codeStore.get(phone);
        if (entry == null) {
            throw new RuntimeException("请先获取验证码");
        }
        if (entry.isExpired()) {
            codeStore.remove(phone);
            throw new RuntimeException("验证码已过期，请重新获取");
        }
        if (!entry.getCode().equals(code)) {
            throw new RuntimeException("验证码错误");
        }

        codeStore.remove(phone);

        boolean isNewUser = !userStore.containsKey(phone);
        if (isNewUser) {
            userStore.put(phone, new User(phone));
        }

        User user = userStore.get(phone);
        String token = jwtUtil.generateToken(user.getId(), user.getPhone());

        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("isNewUser", isNewUser);
        return result;
    }

    String getCodeForTest(String phone) {
        CodeEntry entry = codeStore.get(phone);
        return entry != null ? entry.getCode() : null;
    }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd superpowers-demo && mvn test -Dtest=AuthServiceTest -q`
Expected: Tests run: 7, Failures: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/service/AuthService.java src/test/java/com/example/auth/service/AuthServiceTest.java
git commit -m "feat: 添加 AuthService 及单元测试"
```

---

### Task 7: AuthController + 集成测试

**Files:**
- Create: `src/main/java/com/example/auth/controller/AuthController.java`
- Create: `src/test/java/com/example/auth/controller/AuthControllerTest.java`

- [ ] **Step 1: 写 AuthController 集成测试**

```java
package com.example.auth.controller;

import com.example.auth.service.AuthService;
import com.example.auth.util.JwtUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class AuthControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private AuthService authService;

    @Test
    void sendCode_validPhone_shouldReturn200() throws Exception {
        mockMvc.perform(post("/api/auth/send-code")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13800138000\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.message").value("验证码发送成功"));
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
    void login_correctCode_shouldReturnToken() throws Exception {
        authService.sendCode("13900139000");
        String code = authService.getCodeForTest("13900139000");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13900139000\",\"code\":\"" + code + "\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.isNewUser").value(true));
    }

    @Test
    void login_wrongCode_shouldReturn400() throws Exception {
        authService.sendCode("13700137000");

        mockMvc.perform(post("/api/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"phone\":\"13700137000\",\"code\":\"000000\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value(400))
                .andExpect(jsonPath("$.message").value("验证码错误"));
    }
}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd superpowers-demo && mvn test -Dtest=AuthControllerTest -q 2>&1 | tail -5`
Expected: 编译失败或测试失败（AuthController 类不存在）

- [ ] **Step 3: 实现 AuthController**

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
        return Result.success("验证码发送成功");
    }

    @PostMapping("/login")
    public Result<Map<String, Object>> login(@Valid @RequestBody LoginRequest request) {
        Map<String, Object> data = authService.login(request.getPhone(), request.getCode());
        return Result.success("登录成功", data);
    }
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd superpowers-demo && mvn test -q`
Expected: Tests run: *, Failures: 0, Errors: 0

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/example/auth/controller/AuthController.java src/test/java/com/example/auth/controller/AuthControllerTest.java
git commit -m "feat: 添加 AuthController 及集成测试"
```

---

### Task 8: 全量验证

**Files:** 无新增

- [ ] **Step 1: 运行全部测试**

Run: `cd superpowers-demo && mvn test -q`
Expected: 全部通过

- [ ] **Step 2: 启动应用并手动测试**

Run: `cd superpowers-demo && mvn spring-boot:run -q`

在另一个终端执行：
```bash
# 发送验证码
curl -X POST http://localhost:8080/api/auth/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000"}'

# 从控制台查看验证码，然后用验证码登录
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","code":"实际的验证码"}'
```

Expected: 发送验证码返回 200，登录返回 200 并包含 JWT token

- [ ] **Step 3: 确认完毕，回到项目根目录**

```bash
cd ..
```

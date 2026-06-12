## 手机号验证码登录注册 API 设计文档

### 项目概述

开发一个基于手机号和短信验证码的登录注册合一 API，采用极简教学版方案，只包含发送验证码和登录注册两个核心接口，登录时手机号不存在则自动注册

### 技术栈

- Java 17 + Spring Boot 3.2.5 + Maven
- JWT 库：JJWT 0.12.5（HMAC-SHA256 签名）
- 验证框架：Spring Boot Starter Validation（Jakarta）
- 存储：ConcurrentHashMap 纯内存
- 短信：Mock 实现，验证码打印到控制台日志
- 测试：JUnit 5 + Spring Boot Test + MockMvc

### 项目结构

```
src/main/java/com/example/auth/
├── AuthApplication.java            # Spring Boot 启动类
├── common/
│   └── Result.java                 # 统一响应体 {code, message, data}
├── model/
│   ├── User.java                   # 用户实体 (id, phone, createTime)
│   ├── SendCodeRequest.java        # 发送验证码请求 DTO
│   ├── LoginRequest.java           # 登录请求 DTO
│   └── CodeEntry.java             # 验证码记录 (code, createTime, expireTime)
├── util/
│   └── JwtUtil.java               # JWT 生成与解析工具类
├── service/
│   ├── SmsService.java            # 短信发送接口
│   ├── impl/
│   │   └── MockSmsServiceImpl.java # Mock 短信实现
│   └── AuthService.java           # 核心业务逻辑
└── controller/
    ├── AuthController.java         # 认证接口 (2 个端点)
    └── GlobalExceptionHandler.java # 全局异常处理
```

### 接口设计

#### 发送验证码

- 路径：`POST /api/auth/send-code`
- 请求体：`{"phone": "13800138000"}`
- 校验规则：
  - 手机号不能为空
  - 手机号必须匹配正则 `^1[3-9]\d{9}$`（中国大陆 11 位手机号）
- 业务逻辑：
  1. 校验手机号格式
  2. 检查冷却时间：同一手机号 60 秒内不能重复发送
  3. 生成 6 位随机数字验证码
  4. 存储验证码（有效期 5 分钟）
  5. 调用 SmsService 发送（Mock 模式下打印到控制台）
- 成功响应：
  ```json
  {
    "code": 200,
    "message": "验证码发送成功",
    "data": null
  }
  ```

#### 登录/注册

- 路径：`POST /api/auth/login`
- 请求体：`{"phone": "13800138000", "code": "123456"}`
- 校验规则：
  - 手机号不能为空，格式同上
  - 验证码不能为空，必须 6 位数字
- 业务逻辑：
  1. 校验请求参数
  2. 查找该手机号的验证码记录，不存在则返回"验证码无效"
  3. 检查验证码是否过期（5 分钟），过期则删除并返回"验证码已过期"
  4. 比对验证码，不匹配返回"验证码错误"
  5. 验证通过后删除已使用的验证码
  6. 查找用户：手机号已存在则登录，不存在则自动注册新用户
  7. 生成 JWT Token
  8. 返回 Token 和是否新用户标识
- 成功响应：
  ```json
  {
    "code": 200,
    "message": "登录成功",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiJ9...",
      "isNewUser": true
    }
  }
  ```

### 核心组件

#### Result 统一响应体

```java
public class Result<T> {
    private int code;
    private String message;
    private T data;
    // 静态工厂方法：success(data)、success(message, data)、error(code, message)
}
```

#### User 用户实体

```java
public class User {
    private String id;        // UUID 自动生成
    private String phone;     // 手机号
    private LocalDateTime createTime;  // 注册时间
}
```

#### CodeEntry 验证码记录

```java
public class CodeEntry {
    private String code;              // 6 位验证码
    private LocalDateTime createTime; // 发送时间
    private LocalDateTime expireTime; // 过期时间 = createTime + 5 分钟
}
```

#### JwtUtil 工具类

- `generateToken(String userId, String phone)` — 生成 JWT，payload 包含 userId 和 phone，过期时间 24 小时
- `parseToken(String token)` — 解析 JWT，返回 Claims，失败抛出异常
- 密钥从 `application.yml` 的 `jwt.secret` 读取

#### SmsService 接口

```java
public interface SmsService {
    void sendCode(String phone, String code);
}
```

#### MockSmsServiceImpl

实现 SmsService，将验证码打印到日志：`[Mock SMS] 向 13800138000 发送验证码: 123456`

#### AuthService 核心业务

内部维护两个 ConcurrentHashMap：
- `codeMap: ConcurrentHashMap<String, CodeEntry>` — 手机号 → 验证码记录
- `userMap: ConcurrentHashMap<String, User>` — 手机号 → 用户信息

核心方法：
- `sendCode(String phone)` — 冷却检查 → 生成验证码 → 存储 → 发送
- `login(String phone, String code)` — 校验验证码 → 查找或创建用户 → 生成 Token → 返回结果

#### GlobalExceptionHandler

捕获三类异常：
- `MethodArgumentNotValidException` — 参数校验失败，提取第一条错误消息
- `RuntimeException` — 业务异常（如"验证码已过期"）
- `Exception` — 兜底，返回 500

### 配置

`application.yml`：
- 服务端口 8080
- JWT secret 和过期时间（24 小时）

### 错误处理

所有业务异常和参数校验异常由 GlobalExceptionHandler 统一捕获，返回相同格式的 Result 结构：
```json
{
  "code": 400,
  "message": "手机号格式不正确",
  "data": null
}
```

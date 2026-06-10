# 手机号验证码登录注册 API 设计文档

> 作者：大都督周瑜
> 公众号：IT周瑜
> 微信：it_zhouyu
> <img src="https://cdn.nlark.com/yuque/0/2025/jpeg/365147/1763450681636-7a88629e-9d39-4f2a-bbd8-8ddc0313e964.jpeg" width="126" title="" crop="0,0,1,1" id="tLaRw" class="ne-image">

## 概述

基于手机号 + 验证码的登录注册一体化 API，Java + Spring Boot + Maven 实现。新用户首次验证自动注册，老用户直接登录。

**技术选型**：
- 框架：Spring Boot 3.x + Java 17
- 短信服务：Mock 模式（验证码打印到控制台）
- 存储：纯内存（ConcurrentHashMap）
- 认证：JWT Token
- 构建：Maven

## API 接口设计

### 1. 发送验证码

`POST /api/auth/send-code`

请求体：
```json
{ "phone": "13800138000" }
```

响应：
```json
{ "code": 200, "message": "验证码发送成功" }
```

### 2. 验证码登录/注册

`POST /api/auth/login`

请求体：
```json
{ "phone": "13800138000", "code": "123456" }
```

响应：
```json
{ "code": 200, "message": "登录成功", "data": { "token": "eyJ...", "isNewUser": true } }
```

### 错误响应

统一格式：
```json
{ "code": 400, "message": "具体错误信息" }
```

错误场景：
- 手机号格式不合法
- 60 秒内重复发送验证码
- 验证码错误
- 验证码已过期

## 项目结构

```
superpowers-demo/
├── pom.xml
└── src/main/java/com/example/auth/
    ├── AuthApplication.java
    ├── controller/
    │   └── AuthController.java
    ├── service/
    │   ├── AuthService.java
    │   └── SmsService.java
    ├── service/impl/
    │   └── MockSmsServiceImpl.java
    ├── util/
    │   └── JwtUtil.java
    ├── model/
    │   ├── User.java
    │   ├── SendCodeRequest.java
    │   └── LoginRequest.java
    └── common/
        └── Result.java
```

## 核心组件

| 组件 | 职责 |
|------|------|
| AuthController | 两个 API 端点，参数校验 |
| AuthService | 登录注册业务逻辑，验证码管理，用户管理 |
| SmsService | 短信服务接口，便于后续切换实现 |
| MockSmsServiceImpl | Mock 实现，验证码打印到控制台 |
| JwtUtil | JWT 生成与解析 |
| Result | 统一响应包装类 |

## 核心流程

### 发送验证码

1. 校验手机号格式（11 位数字，1 开头，正则：`^1[3-9]\d{9}$`）
2. 检查 60 秒冷却期，未过冷却期则拒绝
3. 生成 6 位随机数字验证码
4. 存入 ConcurrentHashMap，有效期 5 分钟
5. 调用 SmsService 发送

### 登录/注册

1. 校验手机号和验证码格式
2. 从内存取验证码，校验存在性、匹配性、是否过期
3. 验证通过后立即删除验证码（一次性使用）
4. 查找用户：手机号存在 → 登录，不存在 → 自动创建
5. 生成 JWT（有效期 24 小时），返回 token 和 isNewUser 标记

## 数据模型

### 内存存储

- 验证码：`ConcurrentHashMap<String, CodeEntry>`，key 为手机号
  - CodeEntry 包含：code（验证码）、createTime（创建时间）、expireTime（过期时间）
- 用户：`ConcurrentHashMap<String, User>`，key 为手机号
  - User 包含：id、phone、createTime

### JWT

- 密钥：硬编码固定字符串（仅演示用）
- 有效期：24 小时
- Payload：userId、phone

## 安全策略

- 验证码 5 分钟过期，使用后立即删除
- 同一手机号 60 秒发送冷却期
- 手机号严格格式校验
- JWT 24 小时过期

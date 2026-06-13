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

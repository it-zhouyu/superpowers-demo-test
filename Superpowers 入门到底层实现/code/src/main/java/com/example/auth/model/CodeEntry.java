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

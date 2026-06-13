package com.example.auth.model;

import java.time.LocalDateTime;

public class CodeEntry {

    private String code;
    private LocalDateTime createTime;
    private LocalDateTime expireTime;
    private int attemptCount;

    public CodeEntry(String code, LocalDateTime createTime, LocalDateTime expireTime) {
        this.code = code;
        this.createTime = createTime;
        this.expireTime = expireTime;
        this.attemptCount = 0;
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

    public int getAttemptCount() {
        return attemptCount;
    }

    public void incrementAttemptCount() {
        attemptCount++;
    }
}

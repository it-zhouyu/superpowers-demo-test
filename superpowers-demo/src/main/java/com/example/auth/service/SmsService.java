package com.example.auth.service;

public interface SmsService {

    void sendCode(String phone, String code);
}

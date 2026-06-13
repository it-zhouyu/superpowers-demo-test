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

package com.howardvox.ai;

class VoxSeparationException extends Exception {
    private final String code;
    private final String details;

    VoxSeparationException(String code, String message) {
        this(code, message, null);
    }

    VoxSeparationException(String code, String message, String details) {
        super(message);
        this.code = code;
        this.details = details;
    }

    String getCode() {
        return code;
    }

    String getDetails() {
        return details;
    }
}

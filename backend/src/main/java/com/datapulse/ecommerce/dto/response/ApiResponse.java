package com.datapulse.ecommerce.dto.response;

public class ApiResponse<T> {
    private boolean success; private String message; private T data;
    public ApiResponse() {} public ApiResponse(boolean s, String m, T d) { this.success=s; this.message=m; this.data=d; }
    public boolean isSuccess() { return success; } public String getMessage() { return message; } public T getData() { return data; }
    public void setSuccess(boolean v) { this.success = v; } public void setMessage(String v) { this.message = v; } public void setData(T v) { this.data = v; }

    public static <T> ApiResponse<T> success(T data) { return new ApiResponse<>(true, "Success", data); }
    public static <T> ApiResponse<T> success(String msg, T data) { return new ApiResponse<>(true, msg, data); }
    public static <T> ApiResponse<T> error(String msg) { return new ApiResponse<>(false, msg, null); }
}

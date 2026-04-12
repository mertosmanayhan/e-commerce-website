package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.entity.Category;
import com.datapulse.ecommerce.service.CategoryService;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

@RestController @RequestMapping("/api/categories") @Tag(name="Categories")
public class CategoryController {
    private final CategoryService categoryService;
    public CategoryController(CategoryService cs) { this.categoryService = cs; }
    @GetMapping public ResponseEntity<ApiResponse<List<Category>>> getAll() { return ResponseEntity.ok(ApiResponse.success(categoryService.getAllCategories())); }
    @GetMapping("/root") public ResponseEntity<ApiResponse<List<Category>>> getRoot() { return ResponseEntity.ok(ApiResponse.success(categoryService.getRootCategories())); }
    @GetMapping("/{id}") public ResponseEntity<ApiResponse<Category>> getById(@PathVariable Long id) { return ResponseEntity.ok(ApiResponse.success(categoryService.getCategoryById(id))); }
    @PostMapping @PreAuthorize("hasRole('ADMIN')") public ResponseEntity<ApiResponse<Category>> create(@RequestBody Map<String,Object> body) { Long pid = body.get("parentId")!=null?Long.valueOf(body.get("parentId").toString()):null; return ResponseEntity.ok(ApiResponse.success("Created",categoryService.createCategory((String)body.get("name"),pid))); }
    @PutMapping("/{id}") @PreAuthorize("hasRole('ADMIN')") public ResponseEntity<ApiResponse<Category>> update(@PathVariable Long id, @RequestBody Map<String,String> body) { return ResponseEntity.ok(ApiResponse.success(categoryService.updateCategory(id,body.get("name")))); }
    @DeleteMapping("/{id}") @PreAuthorize("hasRole('ADMIN')") public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) { categoryService.deleteCategory(id); return ResponseEntity.ok(ApiResponse.success("Deleted",null)); }
}

package com.datapulse.ecommerce.controller;
import com.datapulse.ecommerce.dto.request.ProductRequest;
import com.datapulse.ecommerce.dto.response.ApiResponse;
import com.datapulse.ecommerce.dto.response.ProductResponse;
import com.datapulse.ecommerce.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.data.domain.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController @RequestMapping("/api/products") @Tag(name="Products")
public class ProductController {
    private final ProductService productService;
    public ProductController(ProductService ps) { this.productService = ps; }

    @GetMapping @Operation(summary="List products") public ResponseEntity<ApiResponse<Page<ProductResponse>>> getAll(@RequestParam(defaultValue="0") int page, @RequestParam(defaultValue="20") int size, @RequestParam(defaultValue="createdAt") String sortBy, @RequestParam(defaultValue="desc") String sortDir) {
        Sort sort = sortDir.equalsIgnoreCase("asc")?Sort.by(sortBy).ascending():Sort.by(sortBy).descending();
        return ResponseEntity.ok(ApiResponse.success(productService.getAllProducts(PageRequest.of(page,size,sort))));
    }
    @GetMapping("/{id}") @Operation(summary="Get product") public ResponseEntity<ApiResponse<ProductResponse>> getById(@PathVariable Long id) { return ResponseEntity.ok(ApiResponse.success(productService.getProductById(id))); }
    @GetMapping("/search") @Operation(summary="Search") public ResponseEntity<ApiResponse<Page<ProductResponse>>> search(@RequestParam String keyword, @RequestParam(defaultValue="0") int page, @RequestParam(defaultValue="20") int size) { return ResponseEntity.ok(ApiResponse.success(productService.searchProducts(keyword,PageRequest.of(page,size)))); }
    @GetMapping("/category/{categoryId}") public ResponseEntity<ApiResponse<Page<ProductResponse>>> byCategory(@PathVariable Long categoryId, @RequestParam(defaultValue="0") int page, @RequestParam(defaultValue="20") int size) { return ResponseEntity.ok(ApiResponse.success(productService.getProductsByCategory(categoryId,PageRequest.of(page,size)))); }
    @GetMapping("/store/{storeId}") public ResponseEntity<ApiResponse<Page<ProductResponse>>> byStore(@PathVariable Long storeId, @RequestParam(defaultValue="0") int page, @RequestParam(defaultValue="20") int size) { return ResponseEntity.ok(ApiResponse.success(productService.getProductsByStore(storeId,PageRequest.of(page,size)))); }
    @GetMapping("/low-stock") public ResponseEntity<ApiResponse<List<ProductResponse>>> lowStock(@RequestParam(defaultValue="5") Integer threshold) { return ResponseEntity.ok(ApiResponse.success(productService.getLowStockProducts(threshold))); }
    @PostMapping @Operation(summary="Create product") public ResponseEntity<ApiResponse<ProductResponse>> create(@Valid @RequestBody ProductRequest req) { return ResponseEntity.ok(ApiResponse.success("Created",productService.createProduct(req))); }
    @PutMapping("/{id}") @Operation(summary="Update product") public ResponseEntity<ApiResponse<ProductResponse>> update(@PathVariable Long id, @Valid @RequestBody ProductRequest req) { return ResponseEntity.ok(ApiResponse.success("Updated",productService.updateProduct(id,req))); }
    @DeleteMapping("/{id}") @Operation(summary="Delete product") public ResponseEntity<ApiResponse<Void>> delete(@PathVariable Long id) { productService.deleteProduct(id); return ResponseEntity.ok(ApiResponse.success("Deleted",null)); }
}

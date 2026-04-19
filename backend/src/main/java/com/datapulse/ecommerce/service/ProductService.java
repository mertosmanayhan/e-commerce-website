package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.dto.request.ProductRequest;
import com.datapulse.ecommerce.dto.response.ProductResponse;
import com.datapulse.ecommerce.entity.Category;
import com.datapulse.ecommerce.entity.Product;
import com.datapulse.ecommerce.entity.Store;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.CartItemRepository;
import com.datapulse.ecommerce.repository.CategoryRepository;
import com.datapulse.ecommerce.repository.OrderItemRepository;
import com.datapulse.ecommerce.repository.ProductRepository;
import com.datapulse.ecommerce.repository.StoreRepository;
import com.datapulse.ecommerce.repository.WishlistItemRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class ProductService {
    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;
    private final StoreRepository storeRepository;
    private final CartItemRepository cartItemRepository;
    private final WishlistItemRepository wishlistItemRepository;
    private final OrderItemRepository orderItemRepository;

    public ProductService(ProductRepository pr, CategoryRepository cr, StoreRepository sr,
                          CartItemRepository ci, WishlistItemRepository wi, OrderItemRepository oi) {
        this.productRepository = pr;
        this.categoryRepository = cr;
        this.storeRepository = sr;
        this.cartItemRepository = ci;
        this.wishlistItemRepository = wi;
        this.orderItemRepository = oi;
    }

    public Page<ProductResponse> getAllProducts(Pageable p) { return productRepository.findAll(p).map(ProductResponse::fromEntity); }
    public ProductResponse getProductById(Long id) { return ProductResponse.fromEntity(productRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Product","id",id))); }
    public Page<ProductResponse> searchProducts(String kw, Pageable p) { return productRepository.searchProducts(kw, p).map(ProductResponse::fromEntity); }
    public Page<ProductResponse> getProductsByCategory(Long catId, Pageable p) { return productRepository.findByCategoryId(catId, p).map(ProductResponse::fromEntity); }
    public Page<ProductResponse> getProductsByStore(Long storeId, Pageable p) { return productRepository.findByStoreId(storeId, p).map(ProductResponse::fromEntity); }
    public List<ProductResponse> getLowStockProducts(Integer threshold) { return productRepository.findByStockLessThan(threshold).stream().map(ProductResponse::fromEntity).toList(); }
    public Page<ProductResponse> getProductsByStoreOwner(Long ownerId, Pageable p) { return productRepository.findByStoreOwnerId(ownerId, p).map(ProductResponse::fromEntity); }

    @Transactional public ProductResponse createProduct(ProductRequest req) {
        Product p = Product.builder().name(req.getName()).description(req.getDescription()).sku(req.getSku())
                .price(req.getPrice()).stock(req.getStock()).imageUrl(req.getImageUrl()).build();
        if (req.getCategoryId()!=null) p.setCategory(categoryRepository.findById(req.getCategoryId()).orElseThrow(() -> new ResourceNotFoundException("Category","id",req.getCategoryId())));
        if (req.getStoreId()!=null) p.setStore(storeRepository.findById(req.getStoreId()).orElseThrow(() -> new ResourceNotFoundException("Store","id",req.getStoreId())));
        productRepository.save(p); return ProductResponse.fromEntity(p);
    }

    @Transactional public ProductResponse updateProduct(Long id, ProductRequest req) {
        Product p = productRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Product","id",id));
        p.setName(req.getName()); p.setDescription(req.getDescription()); p.setSku(req.getSku());
        p.setPrice(req.getPrice()); p.setStock(req.getStock()); p.setImageUrl(req.getImageUrl());
        if (req.getCategoryId()!=null) p.setCategory(categoryRepository.findById(req.getCategoryId()).orElseThrow(() -> new ResourceNotFoundException("Category","id",req.getCategoryId())));
        if (req.getStoreId()!=null) p.setStore(storeRepository.findById(req.getStoreId()).orElseThrow(() -> new ResourceNotFoundException("Store","id",req.getStoreId())));
        productRepository.save(p); return ProductResponse.fromEntity(p);
    }

    @Transactional
    public void deleteProduct(Long id) {
        if (!productRepository.existsById(id)) throw new ResourceNotFoundException("Product","id",id);
        // Remove FK references before deleting the product
        cartItemRepository.deleteByProductId(id);
        wishlistItemRepository.deleteByProductId(id);
        // Null out order item references (preserve order history, just detach product)
        orderItemRepository.findByProductId(id).forEach(item -> item.setProduct(null));
        orderItemRepository.flush();
        productRepository.deleteById(id);
    }
}

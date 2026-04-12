package com.datapulse.ecommerce.service;

import com.datapulse.ecommerce.entity.Category;
import com.datapulse.ecommerce.exception.ResourceNotFoundException;
import com.datapulse.ecommerce.repository.CategoryRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class CategoryService {
    private final CategoryRepository categoryRepository;
    public CategoryService(CategoryRepository cr) { this.categoryRepository = cr; }

    public List<Category> getAllCategories() { return categoryRepository.findAll(); }
    public List<Category> getRootCategories() { return categoryRepository.findByParentCategoryIsNull(); }
    public Category getCategoryById(Long id) { return categoryRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Category","id",id)); }

    @Transactional public Category createCategory(String name, Long parentId) {
        if (categoryRepository.existsByName(name)) throw new IllegalArgumentException("Category exists: " + name);
        Category c = Category.builder().name(name).build();
        if (parentId != null) c.setParentCategory(categoryRepository.findById(parentId).orElseThrow(() -> new ResourceNotFoundException("Category","id",parentId)));
        return categoryRepository.save(c);
    }

    @Transactional public Category updateCategory(Long id, String name) {
        Category c = categoryRepository.findById(id).orElseThrow(() -> new ResourceNotFoundException("Category","id",id));
        c.setName(name); return categoryRepository.save(c);
    }

    @Transactional public void deleteCategory(Long id) {
        if (!categoryRepository.existsById(id)) throw new ResourceNotFoundException("Category","id",id);
        categoryRepository.deleteById(id);
    }
}

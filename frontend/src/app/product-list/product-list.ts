import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProductService, Product } from '../product.service';
import { CartService } from '../cart.service';
import { WishlistService } from '../wishlist.service';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-product-list',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './product-list.html',
  styleUrl: './product-list.css'
})
export class ProductList implements OnInit {
  products: Product[] = [];
  favoriteIds: Set<number> = new Set();
  cartAddedId: number | null = null;

  searchText: string = '';
  selectedCategory: string = 'Tüm Kategoriler';
  categories: string[] = ['Tüm Kategoriler'];
  sortOption: string = 'En Yeniler';
  minPrice: number | null = null;
  maxPrice: number | null = null;
  selectedRating: number = 0;

  constructor(
    private productService: ProductService,
    private cartService: CartService,
    private wishlistService: WishlistService,
    private cdr: ChangeDetectorRef,
    public authService: AuthService
  ) {}

  get isAuth(): boolean { return this.authService.isAuthenticated(); }
  get currentUser(): any { return this.authService.getCurrentUser(); }

  logout() { this.authService.logout(); }

  ngOnInit() {
    this.productService.getProducts().subscribe({
      next: (data) => {
        this.products = data;
        const uniqueCats = [...new Set(data.map(p => p.category).filter((c): c is string => !!c))].sort();
        this.categories = ['Tüm Kategoriler', ...uniqueCats];
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Ürünler yüklenirken hata:', err)
    });

    this.wishlistService.favorites$.subscribe(favs => {
      this.favoriteIds = new Set(favs.map(f => f.id));
      this.cdr.detectChanges();
    });

    this.cartService.items$.subscribe(() => this.cdr.detectChanges());
  }

  get cartCount(): number { return this.cartService.getTotalItemsCount(); }

  get filteredProducts(): Product[] {
    let filtered = this.products;

    if (this.selectedCategory !== 'Tüm Kategoriler') {
      filtered = filtered.filter(p => p.category === this.selectedCategory);
    }
    if (this.searchText.trim() !== '') {
      const q = this.searchText.toLowerCase();
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(q) || (p.category && p.category.toLowerCase().includes(q))
      );
    }
    if (this.minPrice !== null && this.minPrice > 0) {
      filtered = filtered.filter(p => p.price >= this.minPrice!);
    }
    if (this.maxPrice !== null && this.maxPrice > 0) {
      filtered = filtered.filter(p => p.price <= this.maxPrice!);
    }
    if (this.selectedRating > 0) {
      filtered = filtered.filter(p => p.rating >= this.selectedRating);
    }
    if (this.sortOption === 'Fiyata Göre Artan') {
      filtered.sort((a, b) => a.price - b.price);
    } else if (this.sortOption === 'Fiyata Göre Azalan') {
      filtered.sort((a, b) => b.price - a.price);
    } else if (this.sortOption === 'En Çok Değerlendirilenler') {
      filtered.sort((a, b) => b.reviewCount - a.reviewCount);
    }
    return filtered;
  }

  selectCategory(category: string) { this.selectedCategory = category; }
  getStars(rating: number): string { return '⭐'.repeat(Math.round(rating)); }
  isFavorite(productId: number): boolean { return this.favoriteIds.has(productId); }

  // Misafir de sepete ekleyebilir — login gerekmez
  onAddToCartClick(product: Product) {
    if (product.stock === 0) return;
    this.cartService.addToCart(product);
    this.cartAddedId = product.id;
    setTimeout(() => { this.cartAddedId = null; this.cdr.detectChanges(); }, 1500);
  }

  // Misafir de favoriye ekleyebilir — login gerekmez
  toggleWishlist(product: Product) {
    this.wishlistService.toggleFavorite(product);
  }
}

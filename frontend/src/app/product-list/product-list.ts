import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
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
  showAuthModal: boolean = false;
  selectedProduct: Product | null = null;
  favoriteIds: Set<number> = new Set();

  // Arama ve Kategoriler
  searchText: string = '';
  selectedCategory: string = 'Tüm Kategoriler';
  categories: string[] = ['Tüm Kategoriler'];
  sortOption: string = 'En Yeniler';

  // YENİ: Gelişmiş Filtreler
  minPrice: number | null = null;
  maxPrice: number | null = null;
  selectedRating: number = 0; // 0 = Tüm ürünler

  constructor(
    private productService: ProductService,
    private cartService: CartService,
    private router: Router,
    private wishlistService: WishlistService,
    private cdr: ChangeDetectorRef,
    public authService: AuthService
  ) {}

  get isAuth(): boolean { return this.authService.isAuthenticated(); }
  get currentUser(): any { return this.authService.getCurrentUser(); }
  
  logout() {
    this.authService.logout();
  }

  ngOnInit() {
    this.productService.getProducts().subscribe({
      next: (data) => {
        this.products = data;
        // Kategorileri ürünlerden dinamik olarak oluştur
        const uniqueCats = [...new Set(data.map(p => p.category).filter((c): c is string => !!c))].sort();
        this.categories = ['Tüm Kategoriler', ...uniqueCats];
        this.cdr.detectChanges();
      },
      error: (err) => console.error('Ürünler yüklenirken hata:', err)
    });

    // Favorileri reactive olarak takip et
    this.wishlistService.favorites$.subscribe(favs => {
      this.favoriteIds = new Set(favs.map(f => f.id));
      this.cdr.detectChanges();
    });
  }

  get cartCount(): number {
    return this.cartService.getTotalItemsCount();
  }

  // TÜM FİLTRE VE SIRALAMALARIN UYGULANDIĞI YER
  get filteredProducts(): Product[] {
    let filtered = this.products;

    // 1. Kategori Filtresi
    if (this.selectedCategory !== 'Tüm Kategoriler') {
      filtered = filtered.filter(p => p.category === this.selectedCategory);
    }

    // 2. Canlı Arama (İsim veya Kategori)
    if (this.searchText.trim() !== '') {
      const searchLower = this.searchText.toLowerCase();
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(searchLower) ||
        (p.category && p.category.toLowerCase().includes(searchLower))
      );
    }

    // 3. YENİ: Fiyat Aralığı Filtresi
    if (this.minPrice !== null && this.minPrice > 0) {
      filtered = filtered.filter(p => p.price >= this.minPrice!);
    }
    if (this.maxPrice !== null && this.maxPrice > 0) {
      filtered = filtered.filter(p => p.price <= this.maxPrice!);
    }

    // 4. YENİ: Yıldız Puanı Filtresi (Örn: Sadece 4 ve üzeri)
    if (this.selectedRating > 0) {
      filtered = filtered.filter(p => p.rating >= this.selectedRating);
    }

    // 5. Sıralama İşlemi
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

  onAddToCartClick(product: Product) {
    if (this.isAuth) {
      this.cartService.addToCart(product);
      alert('Ürün sepete eklendi!');
    } else {
      this.selectedProduct = product;
      this.showAuthModal = true;
    }
  }

  continueAsGuest() {
    if (this.selectedProduct) this.cartService.addToCart(this.selectedProduct);
    this.showAuthModal = false;
    this.router.navigate(['/cart']);
  }

  goToLogin() {
    if (this.selectedProduct) this.cartService.addToCart(this.selectedProduct);
    this.showAuthModal = false;
    this.router.navigate(['/login']);
  }

  closeModal() { this.showAuthModal = false; }

  toggleWishlist(product: Product) {
    if (!this.isAuth) {
      this.router.navigate(['/login']);
      return;
    }
    this.wishlistService.toggleFavorite(product);
  }

  isFavorite(productId: number): boolean {
    return this.favoriteIds.has(productId);
  }

}

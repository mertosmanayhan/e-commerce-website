import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { ProductService, Product } from '../product.service';
import { CartService } from '../cart.service';
import { WishlistService } from '../wishlist.service';
import { AuthService } from '../auth.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

interface ReviewItem {
  author: string;
  avatar: string;
  rating: number;
  date: string;
  text: string;
  helpfulCount: number;
}

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './product-detail.html',
  styleUrl: './product-detail.css'
})
export class ProductDetail implements OnInit {
  product: Product | undefined;
  reviews: ReviewItem[] = [];
  loading = true;

  quantity = 1;
  activeTab: 'desc' | 'reviews' | 'specs' = 'desc';
  isFavorite = false;

  newReview = { rating: 5, text: '' };
  hoverStar = 0;
  submittingReview = false;

  toast = { visible: false, message: '', type: 'success' };
  showAuthModal = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private productService: ProductService,
    private cartService: CartService,
    private wishlistService: WishlistService,
    private cdr: ChangeDetectorRef,
    public authService: AuthService,
    private http: HttpClient
  ) {}

  get isAuth() { return this.authService.isAuthenticated(); }
  get currentUser() { return this.authService.getCurrentUser(); }
  get cartCount() { return this.cartService.getTotalItemsCount(); }
  get avgRating(): number {
    if (!this.reviews.length) return this.product?.rating ?? 0;
    return this.reviews.reduce((s, r) => s + r.rating, 0) / this.reviews.length;
  }

  ngOnInit() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.productService.getProductById(id).subscribe({
      next: p => {
        this.product = p;
        this.loading = false;
        this.isFavorite = this.wishlistService.isFavorite(p.id);
        this.loadReviews(id);
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.router.navigate(['/products']); }
    });

    this.wishlistService.favorites$.subscribe(favs => {
      if (this.product) this.isFavorite = favs.some(f => f.id === this.product!.id);
      this.cdr.detectChanges();
    });
  }

  loadReviews(productId: number) {
    this.http.get<any>(`${environment.apiUrl}/reviews/product/${productId}`).subscribe({
      next: res => {
        if (res.success && res.data) {
          this.reviews = res.data.map((r: any) => ({
            author: r.user?.fullName || 'Anonim',
            avatar: (r.user?.fullName || 'A')[0].toUpperCase(),
            rating: r.starRating,
            date: new Date(r.createdAt).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' }),
            text: r.reviewText,
            helpfulCount: r.helpfulVotes ?? 0
          }));
          this.cdr.detectChanges();
        }
      },
      error: () => {}
    });
  }

  addToCart() {
    if (!this.product) return;
    if (!this.isAuth) { this.showAuthModal = true; return; }
    for (let i = 0; i < this.quantity; i++) this.cartService.addToCart(this.product);
    this.showToast(`"${this.product.name}" sepete eklendi! 🛒`, 'success');
  }

  toggleWishlist() {
    if (!this.product) return;
    if (!this.isAuth) { this.router.navigate(['/login']); return; }
    this.wishlistService.toggleFavorite(this.product);
    const msg = this.isFavorite ? 'Favorilerden çıkarıldı' : 'Favorilere eklendi ❤️';
    this.showToast(msg, 'success');
  }

  submitReview() {
    if (!this.isAuth) { this.router.navigate(['/login']); return; }
    if (!this.newReview.text.trim()) { this.showToast('Lütfen bir yorum yazın.', 'error'); return; }
    this.submittingReview = true;

    const payload = { productId: this.product?.id, starRating: this.newReview.rating, reviewText: this.newReview.text };
    this.http.post<any>(`${environment.apiUrl}/reviews`, payload).subscribe({
      next: () => {
        this.reviews.unshift({
          author: this.currentUser?.fullName || 'Sen',
          avatar: (this.currentUser?.fullName || 'S')[0].toUpperCase(),
          rating: this.newReview.rating,
          date: 'Az önce',
          text: this.newReview.text,
          helpfulCount: 0
        });
        this.newReview = { rating: 5, text: '' };
        this.submittingReview = false;
        this.showToast('Yorumunuz başarıyla gönderildi! Teşekkürler 🎉', 'success');
        this.activeTab = 'reviews';
        this.cdr.detectChanges();
      },
      error: () => {
        this.submittingReview = false;
        this.showToast('Yorum gönderilemedi. Lütfen tekrar deneyin.', 'error');
      }
    });
  }

  showToast(message: string, type: 'success' | 'error') {
    this.toast = { visible: true, message, type };
    this.cdr.detectChanges();
    setTimeout(() => { this.toast.visible = false; this.cdr.detectChanges(); }, 3000);
  }

  starsArray(n: number): number[] { return Array(Math.round(n)).fill(0); }
  emptyStarsArray(n: number): number[] { return Array(5 - Math.round(n)).fill(0); }
  getDiscountedPrice(): number { return this.product ? Math.round(this.product.price * 1.25) : 0; }
  getDiscount(): number { return 20; }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
  continueAsGuest() { this.addToCart(); this.showAuthModal = false; this.router.navigate(['/cart']); }
  goToLogin() { this.showAuthModal = false; this.router.navigate(['/login']); }
  closeModal() { this.showAuthModal = false; }
}

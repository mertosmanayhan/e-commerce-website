import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-reviews-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './reviews-page.html',
  styleUrl: './reviews-page.css'
})
export class ReviewsPage implements OnInit {
  loading = true;
  reviews: any[] = [];

  // Write review (INDIVIDUAL)
  showWriteForm = false;
  newReview = { productId: null as number | null, starRating: 5, reviewText: '' };
  products: any[] = [];
  submitting = false;
  submitMsg = '';

  // Respond (CORPORATE)
  respondingId: number | null = null;
  responseText = '';
  savingResponse = false;

  // Filter & sort
  filterRating = 0;
  searchText = '';
  sortOrder: 'newest' | 'oldest' | 'highest' | 'lowest' = 'newest';

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  get user() { return this.authService.getCurrentUser(); }
  get isAdmin()        { return this.user?.role === 'ADMIN'; }
  get isCorporate()    { return this.user?.role === 'CORPORATE'; }
  get isIndividual()   { return this.user?.role === 'INDIVIDUAL'; }
  get canDelete()      { return this.isAdmin || this.isCorporate; }
  get canRespond()     { return this.isCorporate || this.isAdmin; }
  get canWriteReview() { return !!this.user; } // tüm giriş yapmış kullanıcılar

  ngOnInit() {
    if (!this.user) { this.router.navigate(['/login']); return; }
    this.load();
    this.loadProducts(); // tüm roller ürün listesine erişebilmeli (yorum yazmak için)
  }

  load() {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/reviews`).subscribe({
      next: res => { this.reviews = res?.data ?? []; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  loadProducts() {
    this.http.get<any>(`${environment.apiUrl}/products?size=100`).subscribe({
      next: res => { this.products = res?.data?.content ?? res?.data ?? []; }
    });
  }

  get filtered() {
    const ratingNum = Number(this.filterRating);
    let result = this.reviews.filter(r => {
      const rating = r.starRating ?? 0;
      const matchRating = !ratingNum || rating === ratingNum;
      const matchSearch = !this.searchText ||
        (r.productName ?? '').toLowerCase().includes(this.searchText.toLowerCase()) ||
        (r.user?.fullName ?? '').toLowerCase().includes(this.searchText.toLowerCase());
      return matchRating && matchSearch;
    });

    switch (this.sortOrder) {
      case 'newest':  result = [...result].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()); break;
      case 'oldest':  result = [...result].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()); break;
      case 'highest': result = [...result].sort((a, b) => (b.starRating ?? 0) - (a.starRating ?? 0)); break;
      case 'lowest':  result = [...result].sort((a, b) => (a.starRating ?? 0) - (b.starRating ?? 0)); break;
    }
    return result;
  }

  submitReview() {
    if (!this.newReview.productId) return;
    this.submitting = true; this.submitMsg = '';
    this.http.post<any>(`${environment.apiUrl}/reviews`, this.newReview).subscribe({
      next: () => {
        this.submitMsg = 'Yorumunuz gönderildi!';
        this.newReview = { productId: null, starRating: 5, reviewText: '' };
        this.submitting = false;
        this.showWriteForm = false;
        this.load();
      },
      error: () => { this.submitMsg = 'Gönderim başarısız.'; this.submitting = false; }
    });
  }

  startRespond(r: any) {
    this.respondingId = r.id;
    this.responseText = r.corporateResponse ?? '';
  }

  saveResponse(id: number) {
    this.savingResponse = true;
    this.http.patch<any>(`${environment.apiUrl}/reviews/${id}/respond`, { response: this.responseText }).subscribe({
      next: () => {
        const r = this.reviews.find(x => x.id === id);
        if (r) r.corporateResponse = this.responseText;
        this.respondingId = null; this.savingResponse = false;
      },
      error: () => { this.savingResponse = false; }
    });
  }

  deleteReview(id: number) {
    if (!confirm('Bu yorumu silmek istediğinize emin misiniz?')) return;
    this.http.delete<any>(`${environment.apiUrl}/reviews/${id}`).subscribe({
      next: () => { this.reviews = this.reviews.filter(r => r.id !== id); }
    });
  }

  starsArray(n: number)      { return Array(Math.round(Math.min(Math.max(n, 0), 5))).fill(0); }
  emptyStarsArray(n: number) { return Array(5 - Math.round(Math.min(Math.max(n, 0), 5))).fill(0); }

  logout() { this.authService.logout(); }
}

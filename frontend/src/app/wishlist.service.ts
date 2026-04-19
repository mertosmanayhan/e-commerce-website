import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';
import { Product } from './product.service';
import { environment } from '../environments/environment';

import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class WishlistService {
  private favoritesSubject = new BehaviorSubject<Product[]>([]);
  public favorites$ = this.favoritesSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    if (typeof window !== 'undefined') {
      if (localStorage.getItem('token')) {
        this.loadWishlist();
      } else {
        const guest = localStorage.getItem('guestWishlist');
        if (guest) this.favoritesSubject.next(JSON.parse(guest));
      }
    }
  }

  loadWishlist() {
    const token = localStorage.getItem('token');
    if (!token) return;

    this.http.get<any>(`${environment.apiUrl}/wishlist`).subscribe({
      next: (res) => {
        if (res.success) {
          const items = res.data.map((p: any) => ({
            ...p,
            icon: p.imageUrl,
            category: p.categoryName || 'Tüm Kategoriler'
          }));
          this.favoritesSubject.next(items);
        }
      },
      error: (err) => console.warn('Favoriler yüklenemedi:', err.status)
    });
  }

  // Login sonrası misafir favorileri sunucuya aktar, sonra temizle
  mergeGuestWishlist() {
    const raw = localStorage.getItem('guestWishlist');
    if (!raw) return;
    const guestFavs: Product[] = JSON.parse(raw);
    if (guestFavs.length === 0) return;

    const requests = guestFavs.map(p =>
      this.http.post<any>(`${environment.apiUrl}/wishlist`, { productId: p.id }).toPromise().catch(() => {})
    );
    Promise.all(requests).then(() => {
      localStorage.removeItem('guestWishlist');
      this.loadWishlist();
    });
  }

  toggleFavorite(product: Product) {
    const token = localStorage.getItem('token');

    if (!token) {
      // Misafir: localStorage'da tut
      const currentFavs = [...this.favoritesSubject.value];
      if (this.isFavorite(product.id)) {
        const updated = currentFavs.filter(p => p.id !== product.id);
        localStorage.setItem('guestWishlist', JSON.stringify(updated));
        this.favoritesSubject.next(updated);
      } else {
        const newProduct = { ...product, icon: product.imageUrl, category: product.categoryName || product.category };
        const updated = [...currentFavs, newProduct];
        localStorage.setItem('guestWishlist', JSON.stringify(updated));
        this.favoritesSubject.next(updated);
      }
      return;
    }

    const currentFavs = [...this.favoritesSubject.value];

    if (this.isFavorite(product.id)) {
      this.favoritesSubject.next(currentFavs.filter(p => p.id !== product.id));
      this.http.delete<any>(`${environment.apiUrl}/wishlist/${product.id}`).subscribe({
        error: (err) => {
          this.favoritesSubject.next(currentFavs);
          if (err.status === 401) this.router.navigate(['/login']);
        }
      });
    } else {
      const newProduct = { ...product, icon: product.imageUrl, category: product.categoryName || product.category };
      this.favoritesSubject.next([...currentFavs, newProduct]);
      this.http.post<any>(`${environment.apiUrl}/wishlist`, { productId: product.id }).subscribe({
        error: (err) => {
          this.favoritesSubject.next(currentFavs);
          if (err.status === 401) this.router.navigate(['/login']);
        }
      });
    }
  }

  getFavorites(): Product[] {
    if (this.favoritesSubject.value.length === 0 && localStorage.getItem('token')) {
      this.loadWishlist();
    }
    return this.favoritesSubject.value;
  }

  isFavorite(productId: number): boolean {
    return this.favoritesSubject.value.some(p => p.id === productId);
  }
}

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
    if (typeof window !== 'undefined' && localStorage.getItem('token')) {
      this.loadWishlist();
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
      error: (err) => console.warn('Favoriler yüklenemedi (Yetkisiz rol olabilir):', err.status)
    });
  }

  toggleFavorite(product: Product) {
    const token = localStorage.getItem('token');
    if (!token) {
      this.router.navigate(['/login']);
      return;
    }

    const currentFavs = [...this.favoritesSubject.value];

    if (this.isFavorite(product.id)) {
      // Optimistic: Hemen lokal listeden çıkar
      this.favoritesSubject.next(currentFavs.filter(p => p.id !== product.id));
      
      this.http.delete<any>(`${environment.apiUrl}/wishlist/${product.id}`).subscribe({
        next: () => { /* Zaten silindi, sorun yok */ },
        error: (err) => {
          // Başarısız olursa geri al
          this.favoritesSubject.next(currentFavs);
          if (err.status === 401) this.router.navigate(['/login']);
        }
      });
    } else {
      // Optimistic: Hemen lokal listeye ekle
      const newProduct = { ...product, icon: product.imageUrl, category: product.categoryName || product.category };
      this.favoritesSubject.next([...currentFavs, newProduct]);
      
      this.http.post<any>(`${environment.apiUrl}/wishlist`, { productId: product.id }).subscribe({
        next: () => { /* Zaten eklendi */ },
        error: (err) => {
          // Başarısız olursa geri al
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

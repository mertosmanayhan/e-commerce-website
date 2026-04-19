import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';
import { Product } from './product.service';
import { environment } from '../environments/environment';

import { Router } from '@angular/router';

export interface CartItem {
  cartItemId: number;
  product: Product;
  quantity: number;
}

@Injectable({
  providedIn: 'root'
})
export class CartService {
  private itemsSubject = new BehaviorSubject<CartItem[]>([]);
  public items$ = this.itemsSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      if (token) {
        this.loadCart();
      } else {
        const guestCart = localStorage.getItem('guestCart');
        if (guestCart) this.itemsSubject.next(JSON.parse(guestCart));
      }
    }
  }

  // Sepeti Sunucudan Yükle
  loadCart() {
    // Sadece giriş yapmış kullanıcılar sepeti çekebilir (ya da backend hata fırlatmazsa çalışır)
    const token = localStorage.getItem('token');
    if (!token) return;

    this.http.get<any>(`${environment.apiUrl}/cart`).subscribe({
      next: (res) => {
        if (res.success) {
          const mappedItems: CartItem[] = res.data.map((backendItem: any) => ({
            cartItemId: backendItem.id,
            quantity: backendItem.quantity,
            product: {
              id: backendItem.productId,
              name: backendItem.productName,
              sku: backendItem.productSku,
              price: backendItem.price,
              icon: backendItem.imageUrl,
              imageUrl: backendItem.imageUrl,
              description: '', categoryName: '', rating: 0, reviewCount: 0, stock: 0
            }
          }));
          this.itemsSubject.next(mappedItems);
        }
      },
      error: (err) => console.warn('Sepet verisi alınamadı (Yetkisiz rol olabilir):', err.status)
    });
  }

  getItems(): CartItem[] {
    if (this.itemsSubject.value.length === 0) {
      this.loadCart(); // Eğer boşsa tetikle
    }
    return this.itemsSubject.value;
  }

  addToCart(product: Product) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      // Misafir sepetini local storage'da tut
      let guestCart: CartItem[] = [];
      const storedCart = localStorage.getItem('guestCart');
      if (storedCart) guestCart = JSON.parse(storedCart);
      
      const existing = guestCart.find(i => i.product.id === product.id);
      if (existing) {
        existing.quantity += 1;
      } else {
        guestCart.push({ cartItemId: Date.now(), product: product, quantity: 1 });
      }
      localStorage.setItem('guestCart', JSON.stringify(guestCart));
      this.itemsSubject.next(guestCart);
      return;
    }

    this.http.post<any>(`${environment.apiUrl}/cart`, { productId: product.id, quantity: 1 }).subscribe({
      next: () => this.loadCart(),
      error: (err) => {
        console.error('Sepete eklenemedi', err);
        if (err.status === 401) {
           this.router.navigate(['/login']);
        }
      }
    });
  }

  increaseQuantity(productId: number) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const item = this.itemsSubject.value.find(i => i.product.id === productId);
    if (!item) return;

    if (!token) {
      item.quantity += 1;
      localStorage.setItem('guestCart', JSON.stringify(this.itemsSubject.value));
      this.itemsSubject.next([...this.itemsSubject.value]);
      return;
    }
    
    this.http.patch<any>(`${environment.apiUrl}/cart/${item.cartItemId}`, { quantity: item.quantity + 1 }).subscribe({
      next: () => this.loadCart()
    });
  }

  decreaseQuantity(productId: number) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const item = this.itemsSubject.value.find(i => i.product.id === productId);
    if (!item) return;

    if (!token) {
      if (item.quantity > 1) {
        item.quantity -= 1;
        localStorage.setItem('guestCart', JSON.stringify(this.itemsSubject.value));
        this.itemsSubject.next([...this.itemsSubject.value]);
      } else {
        this.removeFromCart(productId);
      }
      return;
    }

    if (item.quantity > 1) {
      this.http.patch<any>(`${environment.apiUrl}/cart/${item.cartItemId}`, { quantity: item.quantity - 1 }).subscribe({
        next: () => this.loadCart()
      });
    } else {
      this.removeFromCart(productId);
    }
  }

  removeFromCart(productId: number) {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const item = this.itemsSubject.value.find(i => i.product.id === productId);
    if (!item) return;

    if (!token) {
      const filtered = this.itemsSubject.value.filter(i => i.product.id !== productId);
      localStorage.setItem('guestCart', JSON.stringify(filtered));
      this.itemsSubject.next(filtered);
      return;
    }

    this.http.delete<any>(`${environment.apiUrl}/cart/${item.cartItemId}`).subscribe({
      next: () => this.loadCart()
    });
  }

  // Login sonrası misafir sepeti sunucuya aktar, sonra temizle
  mergeGuestCart() {
    const raw = localStorage.getItem('guestCart');
    if (!raw) return;
    const guestItems: CartItem[] = JSON.parse(raw);
    if (guestItems.length === 0) return;

    const requests = guestItems.map(item =>
      this.http.post<any>(`${environment.apiUrl}/cart`, { productId: item.product.id, quantity: item.quantity }).toPromise().catch(() => {})
    );
    Promise.all(requests).then(() => {
      localStorage.removeItem('guestCart');
      this.loadCart();
    });
  }

  clearCart() {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      localStorage.removeItem('guestCart');
      this.itemsSubject.next([]);
      return;
    }

    this.http.delete<any>(`${environment.apiUrl}/cart`).subscribe({
      next: () => this.itemsSubject.next([])
    });
  }

  getCartTotal() {
    return this.itemsSubject.value.reduce((total, item) => total + (item.product.price * item.quantity), 0);
  }

  getTotalItemsCount() {
    return this.itemsSubject.value.reduce((count, item) => count + item.quantity, 0);
  }
}

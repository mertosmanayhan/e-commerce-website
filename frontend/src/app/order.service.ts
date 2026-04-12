import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { CartItem } from './cart.service';
import { environment } from '../environments/environment';

export interface Order {
  id?: number;
  orderId: string;
  date: Date;
  total: number;
  totalAmount: number;
  status: string;
  items: any[];
}

@Injectable({
  providedIn: 'root'
})
export class OrderService {
  constructor(private http: HttpClient) {}

  addOrder(items: CartItem[], total: number): Observable<any> {
    const request = {
      paymentMethod: 'Credit Card',
      items: items.map(i => ({ productId: i.product.id, quantity: i.quantity }))
    };
    return this.http.post<any>(`${environment.apiUrl}/orders`, request);
  }

  getOrders(): Observable<Order[]> {
    return this.http.get<any>(`${environment.apiUrl}/orders`).pipe(
      map(res => {
        if (res.success && res.data) {
          // Backend Page format\u0131nda d\u00f6n\u00fcyor: res.data.content dizisi i\u00e7inde sipari\u015fler var
          const orders = res.data.content || res.data;
          if (!Array.isArray(orders)) return [];
          
          return orders.map((o: any) => ({
            id: o.id,
            orderId: o.orderNumber,
            date: new Date(o.orderDate),
            total: o.totalAmount,
            totalAmount: o.totalAmount,
            status: o.status,
            items: (o.items || []).map((item: any) => ({
              quantity: item.quantity,
              product: {
                id: item.productId,
                name: item.productName,
                price: item.unitPrice,
                imageUrl: item.imageUrl || '',
                icon: item.imageUrl || ''
              }
            }))
          }));
        }
        return [];
      })
    );
  }
}

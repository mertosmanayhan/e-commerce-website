import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { CartService, CartItem } from '../cart.service';
import { OrderService } from '../order.service';
import { AuthService } from '../auth.service';
import { environment } from '../../environments/environment';

declare var Stripe: any;

@Component({
  selector: 'app-checkout',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './checkout.html',
  styleUrl: './checkout.css'
})
export class Checkout implements OnInit, OnDestroy {
  cartItems: CartItem[] = [];
  total = 0;

  // Steps: 'shipping' | 'payment' | 'success'
  step: 'shipping' | 'payment' | 'success' = 'shipping';

  shipping = { fullName: '', email: '', phone: '', address: '', city: '', zipCode: '', country: 'Türkiye' };

  paymentMethod: 'card' | 'cash' = 'card';

  isProcessing = false;
  errorMessage = '';
  orderNumber = '';

  // Stripe
  stripe: any = null;
  elements: any = null;
  cardElement: any = null;
  stripeReady = false;
  clientSecret = '';

  countries = ['Türkiye', 'Almanya', 'Fransa', 'İngiltere', 'ABD', 'Hollanda', 'İspanya', 'İtalya'];

  constructor(
    private cartService: CartService,
    private orderService: OrderService,
    private router: Router,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private authService: AuthService
  ) {}

  ngOnInit() {
    const user = this.authService.getCurrentUser();
    if (user?.role === 'CORPORATE' || user?.role === 'ADMIN') {
      // Mağaza sahipleri ve adminler sipariş oluşturamaz
      this.router.navigate(['/dashboard']);
      return;
    }
    this.cartItems = this.cartService.getItems();
    this.total = this.cartService.getCartTotal();
    if (this.cartItems.length === 0) { this.router.navigate(['/products']); return; }
    this.loadStripe();
  }

  ngOnDestroy() {
    if (this.cardElement) this.cardElement.destroy();
  }

  get subtotal() { return this.cartItems.reduce((s, i) => s + i.product.price * i.quantity, 0); }
  get shipping_cost() { return this.subtotal >= 100 ? 0 : 9.99; }
  get tax() { return this.subtotal * 0.08; }
  get grandTotal() { return this.subtotal + this.shipping_cost + this.tax; }
  get itemCount() { return this.cartItems.reduce((s, i) => s + i.quantity, 0); }

  loadStripe() {
    if ((window as any).Stripe) {
      this.initStripe();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://js.stripe.com/v3/';
    script.onload = () => { this.initStripe(); this.cdr.detectChanges(); };
    document.head.appendChild(script);
  }

  initStripe() {
    this.http.get<any>(`${environment.apiUrl}/payment/config`).subscribe({
      next: res => {
        const key = res?.data?.publishableKey;
        if (!key) return;
        this.stripe = Stripe(key);
        this.stripeReady = true;
        this.cdr.detectChanges();
      },
      error: () => { this.stripeReady = false; this.cdr.detectChanges(); }
    });
  }

  goToPayment() {
    if (!this.shipping.fullName || !this.shipping.address || !this.shipping.city) {
      this.errorMessage = 'Lütfen tüm teslimat bilgilerini doldurun.';
      return;
    }
    this.errorMessage = '';
    this.step = 'payment';
    this.cdr.detectChanges();
    if (this.paymentMethod === 'card') {
      setTimeout(() => this.mountCardElement(), 100);
    }
  }

  onPaymentMethodChange() {
    if (this.paymentMethod === 'card') {
      setTimeout(() => this.mountCardElement(), 100);
    } else {
      if (this.cardElement) { this.cardElement.destroy(); this.cardElement = null; }
    }
  }

  mountCardElement() {
    if (!this.stripe || !this.stripeReady) return;
    const container = document.getElementById('card-element');
    if (!container) return;
    if (this.cardElement) this.cardElement.destroy();

    const els = this.stripe.elements();
    this.cardElement = els.create('card', {
      style: {
        base: {
          fontSize: '16px',
          color: '#2d3748',
          fontFamily: '"Segoe UI", sans-serif',
          '::placeholder': { color: '#a0aec0' }
        },
        invalid: { color: '#e53e3e' }
      },
      hidePostalCode: true
    });
    this.cardElement.mount('#card-element');
    this.cardElement.on('change', (e: any) => {
      this.errorMessage = e.error ? e.error.message : '';
      this.cdr.detectChanges();
    });
  }

  async processPayment() {
    this.isProcessing = true;
    this.errorMessage = '';

    if (this.paymentMethod === 'cash') {
      this.placeOrder('CASH_ON_DELIVERY');
      return;
    }

    // Stripe: önce PaymentIntent oluştur
    const amountCents = Math.round(this.grandTotal * 100);
    this.http.post<any>(`${environment.apiUrl}/payment/create-intent`, {
      amount: amountCents,
      currency: 'usd'
    }).subscribe({
      next: async res => {
        const secret = res?.data?.clientSecret;
        if (!secret) { this.isProcessing = false; this.errorMessage = 'Ödeme başlatılamadı.'; this.cdr.detectChanges(); return; }

        // Simülasyon modu — Stripe key olmadan test
        if (secret.startsWith('pi_sim_')) {
          this.placeOrder('CREDIT_CARD');
          return;
        }

        const result = await this.stripe.confirmCardPayment(secret, {
          payment_method: {
            card: this.cardElement,
            billing_details: {
              name: this.shipping.fullName,
              email: this.shipping.email
            }
          }
        });

        if (result.error) {
          this.isProcessing = false;
          this.errorMessage = result.error.message;
          this.cdr.detectChanges();
        } else if (result.paymentIntent?.status === 'succeeded') {
          this.placeOrder('CREDIT_CARD');
        }
      },
      error: () => {
        this.isProcessing = false;
        this.errorMessage = 'Ödeme sunucusuna bağlanılamadı.';
        this.cdr.detectChanges();
      }
    });
  }

  placeOrder(paymentMethod: string) {
    this.orderService.addOrder(this.cartItems, this.grandTotal).subscribe({
      next: (res: any) => {
        this.orderNumber = res?.data?.orderNumber ?? 'ORD-' + Date.now();
        this.cartService.clearCart();
        this.isProcessing = false;
        this.step = 'success';
        this.cdr.detectChanges();
        setTimeout(() => this.router.navigate(['/orders']), 4000);
      },
      error: () => {
        this.isProcessing = false;
        this.errorMessage = 'Sipariş oluşturulurken hata oluştu.';
        this.cdr.detectChanges();
      }
    });
  }
}

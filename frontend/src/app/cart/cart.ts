import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { CartService, CartItem } from '../cart.service';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './cart.html',
  styleUrl: './cart.css'
})
export class CartComponent implements OnInit {
  cartItems: CartItem[] = [];
  total: number = 0;
  isLoggedIn = false;

  constructor(private cartService: CartService, private router: Router) {}

  ngOnInit() {
    this.isLoggedIn = !!localStorage.getItem('token');
    this.cartService.items$.subscribe(items => {
      this.cartItems = items;
      this.total = this.cartService.getCartTotal();
    });
    this.cartService.loadCart();
  }

  increase(productId: number) { this.cartService.increaseQuantity(productId); }
  decrease(productId: number) { this.cartService.decreaseQuantity(productId); }
  remove(productId: number)   { this.cartService.removeFromCart(productId); }

  goToCheckout() {
    if (!this.isLoggedIn) {
      this.router.navigate(['/login'], { queryParams: { returnUrl: '/checkout' } });
    } else {
      this.router.navigate(['/checkout']);
    }
  }
}

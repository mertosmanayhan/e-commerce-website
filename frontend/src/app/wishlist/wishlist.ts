import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { WishlistService } from '../wishlist.service';
import { CartService } from '../cart.service';
import { Product } from '../product.service';

@Component({
  selector: 'app-wishlist',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './wishlist.html',
  styleUrl: '../product-list/product-list.css' // CSS'i tekrar yazmamak için product-list'in tasarımını ödünç alıyoruz!
})
export class Wishlist implements OnInit {
  favorites: Product[] = [];

  constructor(
    private wishlistService: WishlistService,
    private cartService: CartService
  ) {}

  ngOnInit() {
    this.wishlistService.favorites$.subscribe(favs => {
      this.favorites = favs;
    });
    this.wishlistService.loadWishlist();
  }

  removeFromWishlist(product: Product) {
    this.wishlistService.toggleFavorite(product);
  }

  addToCart(product: Product) {
    this.cartService.addToCart(product);
    alert('Ürün sepete eklendi!');
  }
}

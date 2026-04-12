import { Component, OnInit } from '@angular/core';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from '../auth.service';
import { CartService } from '../cart.service';
import { WishlistService } from '../wishlist.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, CommonModule, RouterModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class Login implements OnInit {
  loginData = { email: '', password: '' };
  errorMessage: string = '';
  loggedOutMessage: string = '';
  loading: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private cartService: CartService,
    private wishlistService: WishlistService
  ) {}

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      if (params['loggedOut'] === 'true') {
        this.loggedOutMessage = 'Başarıyla çıkış yaptınız. Tekrar görüşmek üzere!';
      }
    });
  }

  onLogin() {
    this.loading = true;
    this.errorMessage = '';
    this.authService.login(this.loginData.email, this.loginData.password).subscribe({
      next: (res) => {
        this.loading = false;
        if (res.success) {
          // Login sonrası kullanıcı sepeti ve favorilerini anında çek
          this.cartService.loadCart();
          this.wishlistService.loadWishlist();

          const role = res.data.user.role;
          if (role === 'ADMIN') {
            this.router.navigate(['/admin']);
          } else if (role === 'CORPORATE') {
            this.router.navigate(['/dashboard']);
          } else {
            this.router.navigate(['/products']); // INDIVIDUAL → alışveriş
          }
        }
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = 'E-posta veya şifre hatalı!';
      }
    });
  }
}

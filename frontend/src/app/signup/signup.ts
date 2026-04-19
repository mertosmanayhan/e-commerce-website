import { Component } from '@angular/core';
import { Router, RouterModule, ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from '../auth.service';
import { CartService } from '../cart.service';
import { WishlistService } from '../wishlist.service';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [FormsModule, CommonModule, RouterModule],
  templateUrl: './signup.html',
  styleUrls: ['./signup.css']
})
export class Signup {
  form = {
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    gender: '',
    age: null as number | null,
    city: '',
    country: 'Türkiye'
  };

  successMessage = '';
  errorMessage = '';
  loading = false;
  strength = 0;

  calcStrength() {
    const p = this.form.password;
    let s = 0;
    if (p.length >= 6) s++;
    if (p.length >= 10 && /[A-Z]/.test(p)) s++;
    if (/[0-9]/.test(p) && /[^a-zA-Z0-9]/.test(p)) s++;
    this.strength = s;
  }

  private returnUrl = '/products';

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private authService: AuthService,
    private cartService: CartService,
    private wishlistService: WishlistService
  ) {}

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      if (params['returnUrl']) this.returnUrl = params['returnUrl'];
    });
  }

  onSignup() {
    if (this.form.password !== this.form.confirmPassword) {
      this.errorMessage = 'Şifreler birbiriyle uyuşmuyor!';
      return;
    }
    if (this.form.password.length < 6) {
      this.errorMessage = 'Şifre en az 6 karakter olmalıdır.';
      return;
    }

    this.errorMessage = '';
    this.loading = true;

    const payload: any = {
      fullName: this.form.fullName,
      email:    this.form.email,
      password: this.form.password,
      role:     'INDIVIDUAL'
    };
    if (this.form.gender)  payload.gender  = this.form.gender;
    if (this.form.age)     payload.age     = this.form.age;
    if (this.form.city)    payload.city    = this.form.city;
    if (this.form.country) payload.country = this.form.country;

    this.authService.register(payload).subscribe({
      next: (res: any) => {
        this.loading = false;
        if (res?.success === true) {
          // Token varsa otomatik giriş yap ve misafir verilerini aktar
          if (res.data?.accessToken) {
            localStorage.setItem('token', res.data.accessToken);
            localStorage.setItem('user', JSON.stringify(res.data.user));
            this.cartService.mergeGuestCart();
            this.wishlistService.mergeGuestWishlist();
            this.router.navigateByUrl(this.returnUrl);
          } else {
            this.successMessage = 'Hesabınız başarıyla oluşturuldu. Giriş ekranına yönlendiriliyorsunuz...';
            setTimeout(() => this.router.navigate(['/login']), 2500);
          }
        } else {
          this.errorMessage = res?.message || 'Kayıt sırasında bir hata oluştu.';
        }
      },
      error: (err: any) => {
        this.loading = false;
        // HTTP 4xx/5xx durumlarında err.error içinde backend mesajı gelir
        const msg = err?.error?.message || err?.message || err?.error;
        if (typeof msg === 'string') {
          this.errorMessage = msg;
        } else {
          this.errorMessage = 'Kayıt başarısız. Bu e-posta adresi zaten kullanılıyor olabilir.';
        }
      }
    });
  }
}

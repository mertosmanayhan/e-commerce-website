import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './forgot-password.component.html',
  styleUrls: ['./forgot-password.component.css']
})
export class ForgotPasswordComponent {
  email = '';
  newPassword = '';
  confirmPassword = '';
  showPassword = false;
  showConfirm = false;

  loading = false;
  errorMessage = '';
  successMessage = '';

  constructor(private http: HttpClient) {}

  get rules() {
    const p = this.newPassword;
    return [
      { label: 'En az 8 karakter',         ok: p.length >= 8 },
      { label: 'En az bir büyük harf (A-Z)', ok: /[A-Z]/.test(p) },
      { label: 'En az bir küçük harf (a-z)', ok: /[a-z]/.test(p) },
      { label: 'En az bir rakam (0-9)',      ok: /\d/.test(p) },
      { label: 'En az bir özel karakter',    ok: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(p) },
    ];
  }

  get strength(): number {
    return this.rules.filter(r => r.ok).length;
  }

  get strengthLabel(): string {
    const s = this.strength;
    if (s <= 1) return 'Çok Zayıf';
    if (s === 2) return 'Zayıf';
    if (s === 3) return 'Orta';
    if (s === 4) return 'İyi';
    return 'Güçlü';
  }

  get strengthClass(): string {
    const s = this.strength;
    if (s <= 1) return 'very-weak';
    if (s === 2) return 'weak';
    if (s === 3) return 'fair';
    if (s === 4) return 'good';
    return 'strong';
  }

  get passwordsMatch(): boolean {
    return this.confirmPassword.length > 0 && this.newPassword === this.confirmPassword;
  }

  get canSubmit(): boolean {
    return this.strength >= 3 && this.passwordsMatch && this.email.trim().length > 0;
  }

  resetPassword() {
    this.errorMessage = '';
    if (!this.email.trim()) { this.errorMessage = 'E-posta adresi boş bırakılamaz.'; return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.email.trim())) { this.errorMessage = 'Geçerli bir e-posta adresi girin.'; return; }
    if (this.strength < 3) { this.errorMessage = 'Şifre yeterince güçlü değil.'; return; }
    if (!this.passwordsMatch) { this.errorMessage = 'Şifreler eşleşmiyor.'; return; }

    this.loading = true;
    this.http.post<any>(`${environment.apiUrl}/auth/reset-password`, {
      email: this.email.trim(),
      newPassword: this.newPassword
    }).subscribe({
      next: () => {
        this.loading = false;
        this.successMessage = 'Şifreniz başarıyla sıfırlandı!';
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err.error?.message || 'Bir hata oluştu. E-posta adresinizi kontrol edin.';
      }
    });
  }
}

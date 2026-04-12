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
  email: string = '';
  newPassword: string = '';
  
  loading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';

  constructor(private http: HttpClient) {}

  resetPassword() {
    if (!this.email || !this.newPassword) {
      this.errorMessage = 'Lütfen tüm alanları doldurun.';
      return;
    }

    this.loading = true;
    this.errorMessage = '';
    
    this.http.post<any>(`${environment.apiUrl}/auth/reset-password`, {
      email: this.email,
      newPassword: this.newPassword
    }).subscribe({
      next: (res) => {
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

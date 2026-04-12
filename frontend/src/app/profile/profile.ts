import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth.service';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './profile.html',
  styleUrl: './profile.css'
})
export class Profile implements OnInit {
  user: any = null;
  form = { fullName: '', gender: '', age: null as number | null, city: '', country: '' };
  passwordForm = { current: '', newPass: '', confirm: '' };
  loading = false;
  saving = false;
  savingPassword = false;
  successMsg = '';
  errorMsg = '';
  passwordError = '';
  passwordSuccess = '';
  activeTab = 'profile';

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    if (!this.user) { this.router.navigate(['/login']); return; }
    this.form = {
      fullName: this.user.fullName ?? '',
      gender:   this.user.gender   ?? '',
      age:      this.user.age      ?? null,
      city:     this.user.city     ?? '',
      country:  this.user.country  ?? ''
    };
  }

  saveProfile() {
    this.saving = true; this.successMsg = ''; this.errorMsg = '';
    this.http.put<any>(`${environment.apiUrl}/auth/profile`, this.form).subscribe({
      next: res => {
        const updated = res?.data ?? res;
        localStorage.setItem('user', JSON.stringify({ ...this.user, ...updated }));
        this.user = { ...this.user, ...updated };
        this.successMsg = 'Profiliniz başarıyla güncellendi.';
        this.saving = false;
      },
      error: () => { this.errorMsg = 'Güncelleme sırasında hata oluştu.'; this.saving = false; }
    });
  }

  changePassword() {
    this.passwordError = ''; this.passwordSuccess = '';
    if (this.passwordForm.newPass !== this.passwordForm.confirm) {
      this.passwordError = 'Yeni şifreler eşleşmiyor.'; return;
    }
    if (this.passwordForm.newPass.length < 6) {
      this.passwordError = 'Şifre en az 6 karakter olmalı.'; return;
    }
    this.savingPassword = true;
    this.http.post<any>(`${environment.apiUrl}/auth/reset-password`, {
      email: this.user.email,
      newPassword: this.passwordForm.newPass
    }).subscribe({
      next: () => {
        this.passwordSuccess = 'Şifreniz başarıyla değiştirildi.';
        this.passwordForm = { current: '', newPass: '', confirm: '' };
        this.savingPassword = false;
      },
      error: () => { this.passwordError = 'Şifre değiştirme başarısız.'; this.savingPassword = false; }
    });
  }

  logout() { this.authService.logout(); }
}

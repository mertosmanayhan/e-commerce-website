import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-shipments',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './shipments.html',
  styleUrl: './shipments.css'
})
export class Shipments implements OnInit {
  loading = true;
  shipments: any[] = [];
  sortOrder: 'newest' | 'oldest' = 'newest';
  isAdmin = false;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  get user() { return this.authService.getCurrentUser(); }

  ngOnInit() {
    this.isAdmin = this.user?.role === 'ADMIN';
    this.load();
  }

  load() {
    this.http.get<any>(`${environment.apiUrl}/shipments`).subscribe({
      next: res => {
        this.shipments = res?.data ?? [];
        this.applySort();
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  applySort() {
    this.shipments.sort((a, b) => {
      const da = new Date(a.createdAt ?? a.orderDate ?? 0).getTime();
      const db = new Date(b.createdAt ?? b.orderDate ?? 0).getTime();
      return this.sortOrder === 'newest' ? db - da : da - db;
    });
  }

  onSortChange() { this.applySort(); this.cdr.detectChanges(); }

  getStatusClass(status: string) {
    const s = (status || '').toUpperCase();
    if (s === 'DELIVERED') return 'status-delivered';
    if (s === 'SHIPPED' || s === 'IN_TRANSIT') return 'status-shipped';
    if (s === 'CANCELLED') return 'status-cancelled';
    return 'status-pending';
  }

  getStatusLabel(status: string) {
    const s = (status || '').toUpperCase();
    if (s === 'DELIVERED') return 'Teslim Edildi';
    if (s === 'SHIPPED') return 'Kargoda';
    if (s === 'IN_TRANSIT') return 'Yolda';
    if (s === 'CANCELLED') return 'İptal';
    return 'Beklemede';
  }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
}

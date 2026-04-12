import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth.service';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './orders.html',
  styleUrl: './orders.css'
})
export class Orders implements OnInit {
  orders: any[] = [];
  loading = true;
  user: any = null;

  // Filters
  filterStatus = '';
  searchText = '';

  // Pagination
  page = 0;
  pageSize = 10;
  totalPages = 1;
  totalElements = 0;

  readonly statuses = ['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED'];

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  get isCorporate() { return this.user?.role === 'CORPORATE'; }
  get isAdmin()     { return this.user?.role === 'ADMIN'; }

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    if (!this.user) { this.router.navigate(['/login']); return; }
    this.load();
  }

  load() {
    this.loading = true;
    const url = `${environment.apiUrl}/orders?page=${this.page}&size=${this.pageSize}`;
    this.http.get<any>(url).subscribe({
      next: res => {
        const data = res?.data ?? {};
        this.orders = data.content ?? [];
        this.totalPages = data.totalPages ?? 1;
        this.totalElements = data.totalElements ?? this.orders.length;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  get filtered() {
    return this.orders.filter(o => {
      const matchStatus = !this.filterStatus || o.status === this.filterStatus;
      const matchSearch = !this.searchText ||
        o.orderNumber?.toLowerCase().includes(this.searchText.toLowerCase());
      return matchStatus && matchSearch;
    });
  }

  prevPage() { if (this.page > 0) { this.page--; this.load(); } }
  nextPage() { if (this.page < this.totalPages - 1) { this.page++; this.load(); } }

  exportCsv() {
    const url = `${environment.apiUrl}/orders/export/csv`;
    this.http.get(url, { responseType: 'blob' }).subscribe(blob => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'siparisler.csv';
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  statusLabel(s: string) {
    const map: any = { PENDING:'Beklemede', CONFIRMED:'Onaylandı', SHIPPED:'Kargoda', DELIVERED:'Teslim Edildi', CANCELLED:'İptal' };
    return map[s] ?? s;
  }

  statusClass(s: string) {
    const map: any = { PENDING:'status-pending', CONFIRMED:'status-confirmed', SHIPPED:'status-shipped', DELIVERED:'status-delivered', CANCELLED:'status-cancelled' };
    return map[s] ?? '';
  }

  logout() { this.authService.logout(); }
}

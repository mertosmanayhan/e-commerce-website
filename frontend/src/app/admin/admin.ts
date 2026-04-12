import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './admin.html',
  styleUrl: './admin.css'
})
export class AdminPanel implements OnInit {
  activeTab: 'overview' | 'users' | 'stores' | 'audit' | 'comparison' = 'overview';
  loading = false;

  // Overview KPIs
  stats = { totalUsers: 0, totalStores: 0, totalOrders: 0, totalRevenue: '$0' };

  // Users
  users: any[] = [];
  userFilter = '';

  // Stores
  stores: any[] = [];

  // Audit log (son siparişler + kullanıcı kayıtları)
  auditLog: any[] = [];
  loadingAudit = false;
  auditLoaded = false;
  auditError = '';

  // Cross-store comparison
  storeComparison: any[] = [];
  loadingComparison = false;
  comparisonLoaded = false;
  comparisonError = '';

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadOverview();
    this.loadUsers();
    this.loadStores();
  }

  loadOverview() {
    this.http.get<any>(`${environment.apiUrl}/analytics/dashboard`).subscribe({
      next: res => {
        if (res?.data) {
          const d = res.data;
          this.stats = {
            totalUsers:   d.totalCustomers  ?? 0,
            totalStores:  0,
            totalOrders:  d.totalOrders     ?? 0,
            totalRevenue: `$${(d.totalRevenue ?? 0).toLocaleString()}`
          };
        }
      },
      error: () => {}
    });

    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => {
        const list = res?.data?.content ?? res?.data ?? [];
        this.stats.totalStores = list.length;
      },
      error: () => {}
    });
  }

  loadUsers() {
    this.http.get<any>(`${environment.apiUrl}/users`).subscribe({
      next: res => {
        this.users = res?.data?.content ?? res?.data ?? [];
      },
      error: () => {}
    });
  }

  loadStores() {
    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => {
        this.stores = res?.data?.content ?? res?.data ?? [];
      },
      error: () => {}
    });
  }

  get filteredUsers() {
    if (!this.userFilter.trim()) return this.users;
    const q = this.userFilter.toLowerCase();
    return this.users.filter(u =>
      u.fullName?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      u.role?.toLowerCase().includes(q)
    );
  }

  toggleUserSuspend(user: any) {
    this.http.patch<any>(`${environment.apiUrl}/users/${user.id}/suspend`, {}).subscribe({
      next: () => this.loadUsers(),
      error: () => alert('Kullanıcı durumu güncellenemedi.')
    });
  }

  deleteUser(user: any) {
    if (!confirm(`${user.fullName} kullanıcısını silmek istediğinize emin misiniz?`)) return;
    this.http.delete<any>(`${environment.apiUrl}/users/${user.id}`).subscribe({
      next: () => this.loadUsers(),
      error: () => alert('Kullanıcı silinemedi.')
    });
  }

  loadAuditLog() {
    this.loadingAudit = true;
    this.auditError = '';
    this.auditLog = [];

    forkJoin({
      orders: this.http.get<any>(`${environment.apiUrl}/orders?size=20`),
      users:  this.http.get<any>(`${environment.apiUrl}/users`)
    }).subscribe({
      next: ({ orders, users }) => {
        const orderList: any[] = orders?.data?.content ?? orders?.data ?? [];
        const userList:  any[] = Array.isArray(users?.data) ? users.data : [];

        const orderLogs = orderList.map((o: any) => ({
          type: 'order', icon: '🛒',
          title: `Sipariş #${o.orderNumber}`,
          detail: `${o.status} • $${(o.totalAmount ?? 0).toFixed(2)}`,
          time: o.orderDate
        }));

        const userLogs = [...userList].reverse().slice(0, 10).map((u: any) => ({
          type: 'user', icon: '👤',
          title: `Yeni Kullanıcı: ${u.fullName}`,
          detail: `${u.role} • ${u.email}`,
          time: u.createdAt
        }));

        this.auditLog = [...orderLogs, ...userLogs]
          .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
          .slice(0, 30);
        this.loadingAudit = false;
        this.auditLoaded = true;
        this.cdr.detectChanges();
      },
      error: (e) => {
        this.auditError = `Veri alınamadı (HTTP ${e?.status ?? 'hata'})`;
        this.loadingAudit = false;
        this.auditLoaded = true;
        this.cdr.detectChanges();
      }
    });
  }

  loadComparison() {
    this.loadingComparison = true;
    this.comparisonError = '';
    this.storeComparison = [];
    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => {
        const storeList: any[] = Array.isArray(res?.data) ? res.data : (res?.data?.content ?? []);
        this.storeComparison = storeList.map((s: any) => ({
          name: s.name,
          products: s.productCount ?? s.products?.length ?? 0,
          active: s.open ?? true
        }));
        this.loadingComparison = false;
        this.comparisonLoaded = true;
        this.cdr.detectChanges();
      },
      error: (e) => {
        this.comparisonError = `Mağaza verisi alınamadı (${e?.status ?? 'hata'})`;
        this.loadingComparison = false;
        this.comparisonLoaded = true;
        this.cdr.detectChanges();
      }
    });
  }

  toggleStore(store: any) {
    this.http.patch<any>(`${environment.apiUrl}/stores/${store.id}/toggle`, {}).subscribe({
      next: () => this.loadStores(),
      error: () => alert('Mağaza durumu güncellenemedi.')
    });
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  get maxProducts(): number {
    return Math.max(1, ...this.storeComparison.map(s => s.products));
  }

  roleLabel(role: string) {
    const map: Record<string, string> = {
      ADMIN: 'Admin', CORPORATE: 'Kurumsal', INDIVIDUAL: 'Bireysel'
    };
    return map[role] ?? role;
  }

  roleClass(role: string) {
    return role === 'ADMIN' ? 'badge-admin' : role === 'CORPORATE' ? 'badge-corp' : 'badge-ind';
  }
}

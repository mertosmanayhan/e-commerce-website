import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { forkJoin } from 'rxjs';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

type Tab =
  | 'overview'
  | 'users'
  | 'stores'
  | 'reviews'
  | 'comparison'
  | 'audit'
  | 'analytics'
  | 'products'
  | 'orders'
  | 'store-settings'
  | 'shipments'
  | 'ai';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, BaseChartDirective],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {
  activeTab: Tab = 'overview';

  user: any = null;
  get isAdmin()     { return this.user?.role === 'ADMIN'; }
  get isCorporate() { return this.user?.role === 'CORPORATE'; }

  // ── Overview ─────────────────────────────────────────────────
  overviewStats = { totalUsers: 0, totalStores: 0, totalOrders: 0, totalRevenue: '$0', avgRating: '0' };
  overviewLoading = false;

  // ── Analytics ────────────────────────────────────────────────
  analyticsLoading = false;
  kpi = { revenue: '$0', revenueGrowth: '+0%', orders: '0', ordersGrowth: '+0%', customers: '0', customersGrowth: '+0%', rating: '0', ratingGrowth: '+0.0' };
  orderStatus = { pending: 0, shipped: 0, delivered: 0, cancelled: 0 };
  topProducts: any[] = [];
  selectedDays = 30;
  readonly dateRanges = [{ label: 'Son 7 Gün', value: 7 }, { label: 'Son 30 Gün', value: 30 }, { label: 'Son 60 Gün', value: 60 }, { label: 'Son 90 Gün', value: 90 }];
  segments: any = null; loadingSegments = false; showSegments = false;

  salesChartData: any = { labels: [], datasets: [{ data: [], label: 'Günlük Gelir', fill: true, tension: 0.4, borderColor: '#8c52ff', backgroundColor: 'rgba(140,82,255,0.15)', pointBackgroundColor: '#8c52ff' }] };
  salesChartOptions: any = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } } } };
  categoryChartData: any = { labels: [], datasets: [{ data: [], backgroundColor: ['#8c52ff', '#27ae60', '#3498db', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c'] }] };
  categoryChartOptions: any = { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } } };
  statusChartData: any = { labels: ['Beklemede', 'Kargoda', 'Teslim', 'İptal'], datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#f39c12', '#3498db', '#27ae60', '#e74c3c'] }] };
  statusChartOptions: any = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } };

  // ── Users ────────────────────────────────────────────────────
  users: any[] = [];
  usersLoading = false;
  userFilter = '';

  // ── Stores ───────────────────────────────────────────────────
  stores: any[] = [];
  storesLoading = false;
  editingStore: any = null;
  editForm = { name: '', description: '', address: '', email: '' };
  saving = false;
  showNewForm = false;
  newStoreForm = { name: '', description: '', address: '', email: '' };
  creating = false;
  storeToast = { visible: false, message: '', type: 'success' };

  // ── Reviews ──────────────────────────────────────────────────
  reviews: any[] = [];
  reviewsLoading = false;
  reviewsLoaded = false;
  reviewFilterRating = 0;
  reviewSortOrder: 'newest' | 'oldest' | 'highest' | 'lowest' = 'newest';
  reviewSearchText = '';
  respondingId: number | null = null;
  responseText = '';
  savingResponse = false;
  showWriteForm = false;
  newReview = { productId: null as number | null, starRating: 5, reviewText: '' };
  products: any[] = [];
  submittingReview = false;
  submitMsg = '';

  // ── Comparison ───────────────────────────────────────────────
  storeComparison: any[] = [];
  loadingComparison = false;
  comparisonLoaded = false;
  comparisonError = '';

  // ── Audit ────────────────────────────────────────────────────
  auditLog: any[] = [];
  loadingAudit = false;
  auditLoaded = false;
  auditError = '';

  // ── Products ─────────────────────────────────────────────────
  allProducts: any[] = [];
  productsLoading = false;
  productSearch = '';
  productPage = 0;
  productTotalPages = 1;

  // ── Orders ───────────────────────────────────────────────────
  orders: any[] = [];
  ordersLoading = false;
  orderFilterStatus = '';
  orderSearchText = '';
  orderPage = 0;
  orderPageSize = 10;
  orderTotalPages = 1;
  orderTotalElements = 0;
  readonly statuses = ['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED'];

  // ── Store Settings ───────────────────────────────────────────
  settingsStores: any[] = [];
  settingsLoading = false;
  settingsEditingStore: any = null;
  settingsEditForm = { name: '', description: '', address: '', email: '' };
  settingsSaving = false;
  settingsShowNewForm = false;
  settingsNewForm = { name: '', description: '', address: '', email: '', ownerEmail: '', ownerPassword: '' };
  settingsCreating = false;
  settingsNewCredentials: { email: string; password: string } | null = null;
  lowStockProducts: any[] = [];
  loadingStock = false;
  showLowStock = false;

  // ── Shipments ────────────────────────────────────────────────
  shipments: any[] = [];
  shipmentsLoading = false;
  shipmentSortOrder: 'newest' | 'oldest' = 'newest';

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    if (!this.user) { this.router.navigate(['/login']); return; }
    this.loadOverview();
  }

  setTab(tab: Tab) {
    this.activeTab = tab;
    const loaded = {
      users:          () => this.users.length > 0,
      stores:         () => this.stores.length > 0,
      reviews:        () => this.reviewsLoaded,
      comparison:     () => this.comparisonLoaded,
      audit:          () => this.auditLoaded,
      analytics:      () => false, // always reload on date change
      products:       () => this.allProducts.length > 0,
      orders:         () => this.orders.length > 0,
      'store-settings': () => this.settingsStores.length > 0,
      shipments:      () => this.shipments.length > 0,
      overview:       () => false,
      ai:             () => true,
    } as Record<Tab, () => boolean>;

    if (!loaded[tab]?.()) {
      switch (tab) {
        case 'overview':       this.loadOverview();       break;
        case 'users':          this.loadUsers();          break;
        case 'stores':         this.loadStores();         break;
        case 'reviews':        this.loadReviews();        break;
        case 'comparison':     this.loadComparison();     break;
        case 'audit':          this.loadAuditLog();       break;
        case 'analytics':      this.loadAnalytics();      break;
        case 'products':       this.loadProducts();       break;
        case 'orders':         this.loadOrders();         break;
        case 'store-settings': this.loadSettingsStores(); break;
        case 'shipments':      this.loadShipments();      break;
      }
    }
  }

  // ── Overview ─────────────────────────────────────────────────
  loadOverview() {
    this.overviewLoading = true;
    forkJoin({
      dashboard: this.http.get<any>(`${environment.apiUrl}/analytics/dashboard`),
      stores:    this.http.get<any>(`${environment.apiUrl}/stores`)
    }).subscribe({
      next: ({ dashboard, stores }) => {
        const d = dashboard?.data ?? {};
        const list: any[] = Array.isArray(stores?.data) ? stores.data : (stores?.data?.content ?? []);
        this.overviewStats = {
          totalUsers:   d.totalCustomers ?? 0,
          totalStores:  list.length,
          totalOrders:  d.totalOrders ?? 0,
          totalRevenue: `$${(d.totalRevenue ?? 0).toLocaleString()}`,
          avgRating:    (d.averageRating ?? 0).toFixed(1)
        };
        this.overviewLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.overviewLoading = false; this.cdr.detectChanges(); }
    });
  }

  // ── Analytics ────────────────────────────────────────────────
  onDateRangeChange() { this.loadAnalytics(); }

  loadSegments() {
    this.loadingSegments = true;
    this.http.get<any>(`${environment.apiUrl}/analytics/customers`).subscribe({
      next: res => { this.segments = res?.data ?? res; this.loadingSegments = false; this.showSegments = true; this.cdr.detectChanges(); },
      error: () => { this.loadingSegments = false; }
    });
  }

  loadAnalytics() {
    this.analyticsLoading = true;
    this.http.get<any>(`${environment.apiUrl}/analytics/dashboard?days=${this.selectedDays}`).subscribe({
      next: res => {
        const d = res?.data ?? {};
        this.kpi = {
          revenue: `$${(d.totalRevenue ?? 0).toLocaleString()}`, revenueGrowth: d.revenueGrowth ?? '+0%',
          orders: `${d.totalOrders ?? 0}`, ordersGrowth: d.ordersGrowth ?? '+0%',
          customers: `${d.totalCustomers ?? 0}`, customersGrowth: d.customersGrowth ?? '+0%',
          rating: `${d.averageRating ?? 0}`, ratingGrowth: d.ratingGrowth ?? '+0.0'
        };
        this.orderStatus = { pending: d.pendingOrders ?? 0, shipped: d.shippedOrders ?? 0, delivered: d.deliveredOrders ?? 0, cancelled: d.cancelledOrders ?? 0 };
        this.topProducts = d.topProducts ?? [];
        const trend = d.salesTrend?.length ? d.salesTrend : [{ label: 'Pzt', value: 0 }, { label: 'Sal', value: 0 }, { label: 'Çar', value: 0 }, { label: 'Per', value: 0 }, { label: 'Cum', value: 0 }, { label: 'Cmt', value: 0 }, { label: 'Paz', value: 0 }];
        this.salesChartData = { labels: trend.map((p: any) => p.label), datasets: [{ ...this.salesChartData.datasets[0], data: trend.map((p: any) => p.value) }] };
        if (d.categoryBreakdown?.length) {
          this.categoryChartData = { labels: d.categoryBreakdown.map((p: any) => p.label), datasets: [{ ...this.categoryChartData.datasets[0], data: d.categoryBreakdown.map((p: any) => p.value) }] };
        }
        this.statusChartData = { ...this.statusChartData, datasets: [{ ...this.statusChartData.datasets[0], data: [this.orderStatus.pending, this.orderStatus.shipped, this.orderStatus.delivered, this.orderStatus.cancelled] }] };
        this.analyticsLoading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.analyticsLoading = false; this.cdr.detectChanges(); }
    });
  }

  // ── Users ────────────────────────────────────────────────────
  loadUsers() {
    this.usersLoading = true;
    this.http.get<any>(`${environment.apiUrl}/users`).subscribe({
      next: res => { this.users = res?.data?.content ?? res?.data ?? []; this.usersLoading = false; this.cdr.detectChanges(); },
      error: () => { this.usersLoading = false; this.cdr.detectChanges(); }
    });
  }

  get filteredUsers() {
    if (!this.userFilter.trim()) return this.users;
    const q = this.userFilter.toLowerCase();
    return this.users.filter(u => u.fullName?.toLowerCase().includes(q) || u.email?.toLowerCase().includes(q) || u.role?.toLowerCase().includes(q));
  }

  toggleUserSuspend(user: any) {
    this.http.patch<any>(`${environment.apiUrl}/users/${user.id}/suspend`, {}).subscribe({
      next: () => this.loadUsers(), error: () => alert('Kullanıcı durumu güncellenemedi.')
    });
  }

  deleteUser(user: any) {
    if (!confirm(`${user.fullName} kullanıcısını silmek istediğinize emin misiniz?`)) return;
    this.http.delete<any>(`${environment.apiUrl}/users/${user.id}`).subscribe({
      next: () => this.loadUsers(), error: () => alert('Kullanıcı silinemedi.')
    });
  }

  roleLabel(role: string) { const m: any = { ADMIN: 'Admin', CORPORATE: 'Kurumsal', INDIVIDUAL: 'Bireysel' }; return m[role] ?? role; }
  roleClass(role: string) { return role === 'ADMIN' ? 'badge-admin' : role === 'CORPORATE' ? 'badge-corp' : 'badge-ind'; }

  // ── Stores ───────────────────────────────────────────────────
  loadStores() {
    this.storesLoading = true;
    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => { this.stores = res?.data?.content ?? res?.data ?? []; this.storesLoading = false; this.cdr.detectChanges(); },
      error: () => { this.storesLoading = false; this.cdr.detectChanges(); }
    });
  }

  toggleStore(store: any) {
    this.http.patch<any>(`${environment.apiUrl}/stores/${store.id}/toggle`, {}).subscribe({
      next: () => this.loadStores(), error: () => alert('Mağaza durumu güncellenemedi.')
    });
  }

  // ── Reviews ──────────────────────────────────────────────────
  loadReviews() {
    this.reviewsLoading = true;
    this.http.get<any>(`${environment.apiUrl}/reviews`).subscribe({
      next: res => {
        this.reviews = Array.isArray(res?.data) ? res.data : (res?.data?.content ?? []);
        this.reviewsLoading = false; this.reviewsLoaded = true;
        if (!this.products.length) {
          this.http.get<any>(`${environment.apiUrl}/products?size=200`).subscribe({ next: r => { this.products = r?.data?.content ?? r?.data ?? []; } });
        }
        this.cdr.detectChanges();
      },
      error: () => { this.reviewsLoading = false; this.reviewsLoaded = true; this.cdr.detectChanges(); }
    });
  }

  get filteredReviews() {
    const ratingNum = Number(this.reviewFilterRating);
    let r = ratingNum ? this.reviews.filter(x => x.starRating === ratingNum) : [...this.reviews];
    r = r.filter(x => !this.reviewSearchText || (x.productName ?? '').toLowerCase().includes(this.reviewSearchText.toLowerCase()) || (x.user?.fullName ?? '').toLowerCase().includes(this.reviewSearchText.toLowerCase()));
    switch (this.reviewSortOrder) {
      case 'newest':  r.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()); break;
      case 'oldest':  r.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()); break;
      case 'highest': r.sort((a, b) => (b.starRating ?? 0) - (a.starRating ?? 0)); break;
      case 'lowest':  r.sort((a, b) => (a.starRating ?? 0) - (b.starRating ?? 0)); break;
    }
    return r;
  }

  startRespond(r: any) { this.respondingId = r.id; this.responseText = r.corporateResponse ?? ''; }

  saveResponse(id: number) {
    this.savingResponse = true;
    this.http.patch<any>(`${environment.apiUrl}/reviews/${id}/respond`, { response: this.responseText }).subscribe({
      next: () => { const r = this.reviews.find(x => x.id === id); if (r) r.corporateResponse = this.responseText; this.respondingId = null; this.savingResponse = false; this.cdr.detectChanges(); },
      error: () => { this.savingResponse = false; }
    });
  }

  deleteReview(id: number) {
    if (!confirm('Bu yorumu silmek istediğinize emin misiniz?')) return;
    this.http.delete<any>(`${environment.apiUrl}/reviews/${id}`).subscribe({
      next: () => { this.reviews = this.reviews.filter(r => r.id !== id); this.cdr.detectChanges(); }
    });
  }

  submitReview() {
    if (!this.newReview.productId) return;
    this.submittingReview = true; this.submitMsg = '';
    this.http.post<any>(`${environment.apiUrl}/reviews`, this.newReview).subscribe({
      next: () => { this.submitMsg = 'Yorumunuz gönderildi!'; this.newReview = { productId: null, starRating: 5, reviewText: '' }; this.submittingReview = false; this.showWriteForm = false; this.loadReviews(); },
      error: () => { this.submitMsg = 'Gönderim başarısız.'; this.submittingReview = false; }
    });
  }

  starsArray(n: number)      { return Array(Math.round(Math.min(Math.max(n, 0), 5))).fill(0); }
  emptyStarsArray(n: number) { return Array(5 - Math.round(Math.min(Math.max(n, 0), 5))).fill(0); }

  // ── Comparison ───────────────────────────────────────────────
  loadComparison() {
    this.loadingComparison = true; this.comparisonError = ''; this.storeComparison = [];
    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => {
        const list: any[] = Array.isArray(res?.data) ? res.data : (res?.data?.content ?? []);
        this.storeComparison = list.map((s: any) => ({ id: s.id, name: s.name, products: s.productCount ?? s.products?.length ?? 0, active: s.open ?? true, owner: s.owner?.fullName ?? '-' }));
        this.loadingComparison = false; this.comparisonLoaded = true; this.cdr.detectChanges();
      },
      error: (e) => { this.comparisonError = `Veri alınamadı (${e?.status ?? 'hata'})`; this.loadingComparison = false; this.comparisonLoaded = true; this.cdr.detectChanges(); }
    });
  }

  get maxProducts() { return Math.max(1, ...this.storeComparison.map(s => s.products)); }

  // ── Audit ────────────────────────────────────────────────────
  loadAuditLog() {
    this.loadingAudit = true; this.auditError = ''; this.auditLog = [];
    forkJoin({
      orders: this.http.get<any>(`${environment.apiUrl}/orders?size=20`),
      users:  this.http.get<any>(`${environment.apiUrl}/users`)
    }).subscribe({
      next: ({ orders, users }) => {
        const orderList: any[] = orders?.data?.content ?? orders?.data ?? [];
        const userList:  any[] = Array.isArray(users?.data) ? users.data : [];
        const orderLogs = orderList.map((o: any) => ({ type: 'order', icon: '🛒', title: `Sipariş #${o.orderNumber}`, detail: `${o.status} • $${(o.totalAmount ?? 0).toFixed(2)}`, time: o.orderDate }));
        const userLogs  = [...userList].reverse().slice(0, 10).map((u: any) => ({ type: 'user', icon: '👤', title: `Yeni Kullanıcı: ${u.fullName}`, detail: `${u.role} • ${u.email}`, time: u.createdAt }));
        this.auditLog = [...orderLogs, ...userLogs].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime()).slice(0, 30);
        this.loadingAudit = false; this.auditLoaded = true; this.cdr.detectChanges();
      },
      error: (e) => { this.auditError = `Veri alınamadı (HTTP ${e?.status ?? 'hata'})`; this.loadingAudit = false; this.auditLoaded = true; this.cdr.detectChanges(); }
    });
  }

  // ── Products ─────────────────────────────────────────────────
  loadProducts() {
    this.productsLoading = true;
    this.http.get<any>(`${environment.apiUrl}/products?page=${this.productPage}&size=20`).subscribe({
      next: res => {
        const d = res?.data ?? {};
        this.allProducts = d.content ?? [];
        this.productTotalPages = d.totalPages ?? 1;
        this.productsLoading = false; this.cdr.detectChanges();
      },
      error: () => { this.productsLoading = false; this.cdr.detectChanges(); }
    });
  }

  get filteredProducts() {
    if (!this.productSearch.trim()) return this.allProducts;
    const q = this.productSearch.toLowerCase();
    return this.allProducts.filter(p => p.name?.toLowerCase().includes(q) || p.category?.toLowerCase().includes(q));
  }

  productPrev() { if (this.productPage > 0) { this.productPage--; this.loadProducts(); } }
  productNext() { if (this.productPage < this.productTotalPages - 1) { this.productPage++; this.loadProducts(); } }

  deleteProduct(product: any) {
    if (!confirm(`"${product.name}" ürününü silmek istediğinizden emin misiniz?`)) return;
    this.http.delete(`${environment.apiUrl}/products/${product.id}`).subscribe({
      next: () => { this.showStoreToast('Ürün silindi.', 'success'); this.loadProducts(); },
      error: () => this.showStoreToast('Ürün silinemedi.', 'error')
    });
  }

  // ── Orders ───────────────────────────────────────────────────
  loadOrders() {
    this.ordersLoading = true;
    this.http.get<any>(`${environment.apiUrl}/orders?page=${this.orderPage}&size=${this.orderPageSize}`).subscribe({
      next: res => {
        const data = res?.data ?? {};
        this.orders = data.content ?? [];
        this.orderTotalPages = data.totalPages ?? 1;
        this.orderTotalElements = data.totalElements ?? this.orders.length;
        this.ordersLoading = false; this.cdr.detectChanges();
      },
      error: () => { this.ordersLoading = false; this.cdr.detectChanges(); }
    });
  }

  get filteredOrders() {
    return this.orders.filter(o => {
      const matchStatus = !this.orderFilterStatus || o.status === this.orderFilterStatus;
      const matchSearch = !this.orderSearchText || o.orderNumber?.toLowerCase().includes(this.orderSearchText.toLowerCase());
      return matchStatus && matchSearch;
    });
  }

  orderPrevPage() { if (this.orderPage > 0) { this.orderPage--; this.loadOrders(); } }
  orderNextPage() { if (this.orderPage < this.orderTotalPages - 1) { this.orderPage++; this.loadOrders(); } }

  exportCsv() {
    this.http.get(`${environment.apiUrl}/orders/export/csv`, { responseType: 'blob' }).subscribe(blob => {
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'siparisler.csv'; a.click(); URL.revokeObjectURL(a.href);
    });
  }

  orderStatusLabel(s: string) { const m: any = { PENDING: 'Beklemede', CONFIRMED: 'Onaylandı', SHIPPED: 'Kargoda', DELIVERED: 'Teslim Edildi', CANCELLED: 'İptal' }; return m[s] ?? s; }
  orderStatusClass(s: string) { const m: any = { PENDING: 'status-pending', CONFIRMED: 'status-confirmed', SHIPPED: 'status-shipped', DELIVERED: 'status-delivered', CANCELLED: 'status-cancelled' }; return m[s] ?? ''; }

  // ── Store Settings ───────────────────────────────────────────
  loadSettingsStores() {
    this.settingsLoading = true;
    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => { this.settingsStores = res?.data?.content ?? res?.data ?? []; this.settingsLoading = false; this.cdr.detectChanges(); },
      error: () => { this.settingsLoading = false; this.cdr.detectChanges(); }
    });
  }

  loadLowStock() {
    this.loadingStock = true;
    this.http.get<any>(`${environment.apiUrl}/products/low-stock?threshold=10`).subscribe({
      next: res => { const d = res?.data ?? res; this.lowStockProducts = Array.isArray(d) ? d : d?.content ?? []; this.loadingStock = false; this.showLowStock = true; this.cdr.detectChanges(); },
      error: () => { this.loadingStock = false; }
    });
  }

  startEdit(store: any) { this.settingsEditingStore = store; this.settingsEditForm = { name: store.name ?? '', description: store.description ?? '', address: store.address ?? '', email: store.email ?? '' }; }

  saveEdit() {
    this.settingsSaving = true;
    this.http.put<any>(`${environment.apiUrl}/stores/${this.settingsEditingStore.id}`, this.settingsEditForm).subscribe({
      next: () => { const i = this.settingsStores.findIndex(s => s.id === this.settingsEditingStore.id); if (i >= 0) this.settingsStores[i] = { ...this.settingsStores[i], ...this.settingsEditForm }; this.settingsEditingStore = null; this.settingsSaving = false; this.showStoreToast('Mağaza güncellendi.', 'success'); this.cdr.detectChanges(); },
      error: () => { this.settingsSaving = false; this.showStoreToast('Güncelleme başarısız.', 'error'); }
    });
  }

  createStore() {
    if (!this.settingsNewForm.name.trim()) { this.showStoreToast('Mağaza adı zorunludur.', 'error'); return; }
    this.settingsCreating = true;
    const generatedPassword = this.generateStorePassword();
    const payload = { ...this.settingsNewForm, ownerPassword: generatedPassword };
    this.http.post<any>(`${environment.apiUrl}/stores`, payload).subscribe({
      next: res => {
        const created = res?.data ?? payload;
        this.settingsStores.push(created);
        this.settingsNewCredentials = { email: this.settingsNewForm.ownerEmail || created.owner?.email || '', password: generatedPassword };
        this.settingsNewForm = { name: '', description: '', address: '', email: '', ownerEmail: '', ownerPassword: '' };
        this.settingsShowNewForm = false;
        this.settingsCreating = false;
        this.showStoreToast('Mağaza oluşturuldu.', 'success');
        this.cdr.detectChanges();
      },
      error: () => { this.settingsCreating = false; this.showStoreToast('Oluşturma başarısız.', 'error'); }
    });
  }

  deleteSettingsStore(store: any) {
    if (!confirm(`"${store.name}" mağazasını kalıcı olarak silmek istediğinizden emin misiniz?`)) return;
    this.http.delete<any>(`${environment.apiUrl}/stores/${store.id}`).subscribe({
      next: () => { this.settingsStores = this.settingsStores.filter(s => s.id !== store.id); this.showStoreToast('Mağaza silindi.', 'success'); this.cdr.detectChanges(); },
      error: () => this.showStoreToast('Silme işlemi başarısız.', 'error')
    });
  }

  dismissSettingsCredentials() { this.settingsNewCredentials = null; this.cdr.detectChanges(); }

  private generateStorePassword(): string {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#';
    let pwd = '';
    for (let i = 0; i < 12; i++) pwd += chars[Math.floor(Math.random() * chars.length)];
    return pwd;
  }

  toggleSettingsStore(store: any) {
    this.http.patch<any>(`${environment.apiUrl}/stores/${store.id}/toggle`, {}).subscribe({
      next: res => { const s = this.settingsStores.find(x => x.id === store.id); if (s) s.open = res?.data?.open ?? !s.open; this.showStoreToast('Mağaza durumu güncellendi.', 'success'); this.cdr.detectChanges(); },
      error: () => this.showStoreToast('İşlem başarısız.', 'error')
    });
  }

  showStoreToast(message: string, type: 'success' | 'error') {
    this.storeToast = { visible: true, message, type }; this.cdr.detectChanges();
    setTimeout(() => { this.storeToast.visible = false; this.cdr.detectChanges(); }, 3000);
  }

  stockClass(stock: number) { if (stock === 0) return 'stock-zero'; if (stock <= 5) return 'stock-critical'; return 'stock-low'; }

  // ── Shipments ────────────────────────────────────────────────
  loadShipments() {
    this.shipmentsLoading = true;
    this.http.get<any>(`${environment.apiUrl}/shipments`).subscribe({
      next: res => { this.shipments = res?.data ?? []; this.applyShipmentSort(); this.shipmentsLoading = false; this.cdr.detectChanges(); },
      error: () => { this.shipmentsLoading = false; this.cdr.detectChanges(); }
    });
  }

  applyShipmentSort() {
    this.shipments.sort((a, b) => {
      const da = new Date(a.createdAt ?? a.orderDate ?? 0).getTime();
      const db = new Date(b.createdAt ?? b.orderDate ?? 0).getTime();
      return this.shipmentSortOrder === 'newest' ? db - da : da - db;
    });
  }

  onShipmentSortChange() { this.applyShipmentSort(); this.cdr.detectChanges(); }

  shipmentStatusClass(s: string) { const v = (s || '').toUpperCase(); if (v === 'DELIVERED') return 'status-delivered'; if (v === 'SHIPPED' || v === 'IN_TRANSIT') return 'status-shipped'; if (v === 'CANCELLED') return 'status-cancelled'; return 'status-pending'; }
  shipmentStatusLabel(s: string) { const v = (s || '').toUpperCase(); if (v === 'DELIVERED') return 'Teslim Edildi'; if (v === 'SHIPPED') return 'Kargoda'; if (v === 'IN_TRANSIT') return 'Yolda'; if (v === 'CANCELLED') return 'İptal'; return 'Beklemede'; }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
}

import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-store-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './store-settings.html',
  styleUrl: './store-settings.css'
})
export class StoreSettings implements OnInit {
  loading = true;
  stores: any[] = [];
  lowStockProducts: any[] = [];
  loadingStock = false;
  showLowStock = false;
  isAdmin = false;
  isCorporate = false;
  toast = { visible: false, message: '', type: 'success' };

  // Edit store
  editingStore: any = null;
  editForm = { name: '', description: '', address: '', email: '' };
  saving = false;

  // New store (CORPORATE)
  showNewForm = false;
  newForm = { name: '', description: '', address: '', email: '' };
  creating = false;

  readonly lowStockThreshold = 10;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  get user() { return this.authService.getCurrentUser(); }

  ngOnInit() {
    this.isAdmin     = this.user?.role === 'ADMIN';
    this.isCorporate = this.user?.role === 'CORPORATE';
    this.load();
  }

  load() {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/stores`).subscribe({
      next: res => { this.stores = res?.data ?? []; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  loadLowStock() {
    this.loadingStock = true;
    this.http.get<any>(`${environment.apiUrl}/products/low-stock?threshold=${this.lowStockThreshold}`).subscribe({
      next: res => {
        const data = res?.data ?? res;
        this.lowStockProducts = Array.isArray(data) ? data : data?.content ?? [];
        this.loadingStock = false;
        this.showLowStock = true;
        this.cdr.detectChanges();
      },
      error: () => { this.loadingStock = false; }
    });
  }

  startEdit(store: any) {
    this.editingStore = store;
    this.editForm = { name: store.name ?? '', description: store.description ?? '', address: store.address ?? '', email: store.email ?? '' };
  }

  saveEdit() {
    this.saving = true;
    this.http.put<any>(`${environment.apiUrl}/stores/${this.editingStore.id}`, this.editForm).subscribe({
      next: res => {
        const idx = this.stores.findIndex(s => s.id === this.editingStore.id);
        if (idx >= 0) this.stores[idx] = { ...this.stores[idx], ...this.editForm };
        this.editingStore = null;
        this.saving = false;
        this.showToast('Mağaza başarıyla güncellendi.', 'success');
        this.cdr.detectChanges();
      },
      error: () => { this.saving = false; this.showToast('Güncelleme başarısız.', 'error'); }
    });
  }

  createStore() {
    this.creating = true;
    this.http.post<any>(`${environment.apiUrl}/stores`, this.newForm).subscribe({
      next: res => {
        this.stores.push(res?.data ?? this.newForm);
        this.newForm = { name: '', description: '', address: '', email: '' };
        this.showNewForm = false;
        this.creating = false;
        this.showToast('Mağaza oluşturuldu.', 'success');
        this.cdr.detectChanges();
      },
      error: () => { this.creating = false; this.showToast('Oluşturma başarısız.', 'error'); }
    });
  }

  toggleStore(store: any) {
    this.http.patch<any>(`${environment.apiUrl}/stores/${store.id}/toggle`, {}).subscribe({
      next: res => {
        const s = this.stores.find(x => x.id === store.id);
        if (s) s.open = res?.data?.open ?? !s.open;
        this.showToast('Mağaza durumu güncellendi.', 'success');
        this.cdr.detectChanges();
      },
      error: () => this.showToast('İşlem başarısız.', 'error')
    });
  }

  showToast(message: string, type: 'success' | 'error') {
    this.toast = { visible: true, message, type };
    this.cdr.detectChanges();
    setTimeout(() => { this.toast.visible = false; this.cdr.detectChanges(); }, 3000);
  }

  stockClass(stock: number) {
    if (stock === 0) return 'stock-zero';
    if (stock <= 5) return 'stock-critical';
    return 'stock-low';
  }

  logout() { this.authService.logout(); }
}

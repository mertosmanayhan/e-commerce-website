import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-product-manage',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './product-manage.html',
  styleUrl: './product-manage.css'
})
export class ProductManage implements OnInit {
  products: any[] = [];
  filtered: any[] = [];
  categories: any[] = [];
  loading = true;
  toast = { visible: false, message: '', type: 'success' };

  selectedCategory: number | null = null;
  searchText = '';

  isAdmin = false;
  isCorporate = false;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    const user = this.authService.getCurrentUser();
    this.isAdmin     = user?.role === 'ADMIN';
    this.isCorporate = user?.role === 'CORPORATE';
    this.loadProducts();
    this.loadCategories();
  }

  loadProducts(): void {
    this.loading = true;
    this.http.get<any>(`${environment.apiUrl}/products?size=200`).subscribe({
      next: res => {
        this.products = res?.data?.content ?? res?.data ?? res?.content ?? (Array.isArray(res) ? res : []);
        this.applyFilter();
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  loadCategories(): void {
    this.http.get<any>(`${environment.apiUrl}/categories`).subscribe({
      next: res => { this.categories = res?.data ?? res ?? []; }
    });
  }

  applyFilter(): void {
    let list = [...this.products];
    if (this.selectedCategory !== null) {
      list = list.filter(p => p.categoryId === this.selectedCategory || p.category?.id === this.selectedCategory);
    }
    if (this.searchText.trim()) {
      const q = this.searchText.trim().toLowerCase();
      list = list.filter(p => p.name?.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q));
    }
    this.filtered = list;
  }

  onSearch(): void { this.applyFilter(); }
  onCategoryChange(): void { this.applyFilter(); }

  deleteProduct(product: any): void {
    if (!confirm(`"${product.name}" ürününü silmek istediğinizden emin misiniz?`)) return;
    this.http.delete(`${environment.apiUrl}/products/${product.id}`).subscribe({
      next: () => {
        this.showToast('Ürün silindi.', 'success');
        this.loadProducts();
      },
      error: () => this.showToast('Ürün silinemedi.', 'error')
    });
  }

  goCreate(): void { this.router.navigate(['/dashboard/product-create']); }

  showToast(message: string, type: 'success' | 'error'): void {
    this.toast = { visible: true, message, type };
    setTimeout(() => { this.toast.visible = false; this.cdr.detectChanges(); }, 3000);
  }

  categoryName(product: any): string {
    return product.category?.name ?? product.categoryName ?? '-';
  }
}

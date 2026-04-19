import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
interface Category { id: number; name: string; }

@Component({
  selector: 'app-product-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './product-create.html',
  styleUrls: ['./product-create.css']
})
export class ProductCreate implements OnInit {
  form!: FormGroup;
  categories: Category[] = [];
  submitting = false;
  successMsg = '';
  errorMsg = '';

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      name:        ['', [Validators.required, Validators.minLength(2), Validators.maxLength(200)]],
      description: ['', [Validators.maxLength(1000)]],
      price:       [null, [Validators.required, Validators.min(0.01)]],
      stock:       [null, [Validators.required, Validators.min(0), Validators.pattern('^[0-9]+$')]],
      categoryId:  [null],
      sku:         [''],
      imageUrl:    ['']
    });

    this.loadCategories();
  }

  private loadCategories(): void {
    this.http.get<any>(`${environment.apiUrl}/categories`).subscribe({
      next: res => { this.categories = res.data ?? res ?? []; },
      error: () => {}
    });
  }

  fieldError(name: string): string {
    const ctrl = this.form.get(name);
    if (!ctrl || !ctrl.touched || ctrl.valid) return '';
    if (ctrl.errors?.['required']) return 'Bu alan zorunludur.';
    if (ctrl.errors?.['minlength']) return `En az ${ctrl.errors['minlength'].requiredLength} karakter giriniz.`;
    if (ctrl.errors?.['maxlength']) return `En fazla ${ctrl.errors['maxlength'].requiredLength} karakter giriniz.`;
    if (ctrl.errors?.['min']) return 'Değer 0\'dan büyük olmalıdır.';
    if (ctrl.errors?.['pattern']) return 'Geçerli bir tam sayı giriniz.';
    return '';
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitting = true;
    this.successMsg = '';
    this.errorMsg = '';

    const body = { ...this.form.value };
    body.stock = parseInt(body.stock, 10);

    this.http.post<any>(`${environment.apiUrl}/products/my-store`, body).subscribe({
      next: () => {
        this.successMsg = 'Ürün başarıyla eklendi!';
        this.submitting = false;
        this.form.reset();
        setTimeout(() => this.router.navigate(['/dashboard']), 1500);
      },
      error: err => {
        this.errorMsg = err?.error?.message ?? 'Ürün eklenirken bir hata oluştu.';
        this.submitting = false;
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/dashboard']);
  }
}

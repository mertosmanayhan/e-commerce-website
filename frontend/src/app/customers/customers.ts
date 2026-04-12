import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-customers',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './customers.html',
  styleUrl: './customers.css'
})
export class Customers implements OnInit {
  loading = true;
  users: any[] = [];
  filtered: any[] = [];
  search = '';
  roleFilter = '';
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
    this.http.get<any>(`${environment.apiUrl}/users`).subscribe({
      next: res => {
        this.users = res?.data ?? [];
        this.applyFilter();
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  applyFilter() {
    this.filtered = this.users.filter(u => {
      const matchSearch = !this.search ||
        u.fullName?.toLowerCase().includes(this.search.toLowerCase()) ||
        u.email?.toLowerCase().includes(this.search.toLowerCase());
      const matchRole = !this.roleFilter || u.role === this.roleFilter;
      return matchSearch && matchRole;
    });
  }

  getRoleBadge(role: string) {
    if (role === 'ADMIN') return 'badge-admin';
    if (role === 'CORPORATE') return 'badge-corporate';
    return 'badge-individual';
  }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
}

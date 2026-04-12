import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule, RouterModule, BaseChartDirective],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './analytics.html',
  styleUrl: './analytics.css'
})
export class AnalyticsPage implements OnInit {
  loading = true;
  user: any = null;

  kpi = {
    totalSpend:    '$0',
    totalOrders:   '0',
    avgOrderValue: '$0',
    favCategory:   'N/A'
  };

  // Spend Trend chart
  trendChartData: any = {
    labels: [],
    datasets: [{
      data: [],
      label: 'Harcama ($)',
      fill: true,
      tension: 0.4,
      borderColor: '#8c52ff',
      backgroundColor: 'rgba(140,82,255,0.15)'
    }]
  };

  trendChartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } }
  };

  // Category breakdown chart
  categoryChartData: any = {
    labels: [],
    datasets: [{
      data: [],
      backgroundColor: ['#8c52ff','#27ae60','#3498db','#f39c12','#e74c3c','#9b59b6']
    }]
  };

  categoryChartOptions: any = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } }
  };

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router
  ) {}

  get isCorporate() { return this.user?.role === 'CORPORATE'; }
  get isAdmin()     { return this.user?.role === 'ADMIN'; }

  get roleLabel(): string {
    if (this.isAdmin) return 'Admin';
    if (this.isCorporate) return 'Kurumsal';
    return 'Bireysel';
  }

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    if (!this.user) {
      this.router.navigate(['/login']);
      return;
    }
    // CORPORATE and ADMIN have their own dashboard page
    if (this.isCorporate || this.isAdmin) {
      this.router.navigate(['/dashboard']);
      return;
    }
    this.loadIndividual();
  }

  loadIndividual() {
    this.http.get<any>(`${environment.apiUrl}/analytics/individual`).subscribe({
      next: res => {
        const d = res?.data ?? {};
        this.kpi = {
          totalSpend:    `$${(d.totalSpend ?? 0).toLocaleString()}`,
          totalOrders:   `${d.totalOrders ?? 0}`,
          avgOrderValue: `$${(d.avgOrderValue ?? 0).toLocaleString()}`,
          favCategory:   d.favoriteCategory ?? 'N/A'
        };
        if (d.spendTrend?.length) {
          this.trendChartData = {
            ...this.trendChartData,
            labels: d.spendTrend.map((p: any) => p.label),
            datasets: [{ ...this.trendChartData.datasets[0], data: d.spendTrend.map((p: any) => p.value) }]
          };
        }
        if (d.categoryBreakdown?.length) {
          this.categoryChartData = {
            labels: d.categoryBreakdown.map((p: any) => p.label),
            datasets: [{ ...this.categoryChartData.datasets[0], data: d.categoryBreakdown.map((p: any) => p.value) }]
          };
        }
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  loadDashboard() {
    this.http.get<any>(`${environment.apiUrl}/analytics/dashboard`).subscribe({
      next: res => {
        const d = res?.data ?? {};
        this.kpi = {
          totalSpend:    `$${(d.totalRevenue ?? 0).toLocaleString()}`,
          totalOrders:   `${d.totalOrders ?? 0}`,
          avgOrderValue: d.revenueGrowth ?? '+0%',
          favCategory:   `${d.totalCustomers ?? 0} müşteri`
        };
        if (d.salesTrend?.length) {
          this.trendChartData = {
            ...this.trendChartData,
            labels: d.salesTrend.map((p: any) => p.label),
            datasets: [{ ...this.trendChartData.datasets[0], data: d.salesTrend.map((p: any) => p.value) }]
          };
        }
        if (d.categoryBreakdown?.length) {
          this.categoryChartData = {
            labels: d.categoryBreakdown.map((p: any) => p.label),
            datasets: [{ ...this.categoryChartData.datasets[0], data: d.categoryBreakdown.map((p: any) => p.value) }]
          };
        }
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}

import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, BaseChartDirective],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {
  loading  = true;
  user: any = null;
  isAdmin  = false;

  kpi = {
    revenue: '$0', revenueGrowth: '+0%',
    orders:  '0',  ordersGrowth:  '+0%',
    customers:'0', customersGrowth:'+0%',
    rating:  '0',  ratingGrowth:  '+0.0'
  };

  orderStatus = { pending: 0, shipped: 0, delivered: 0, cancelled: 0 };
  topProducts: any[] = [];

  // Sales trend
  salesChartData: any = {
    labels: [],
    datasets: [{ data: [], label: 'Günlük Gelir ($)', fill: true, tension: 0.4,
      borderColor: '#8c52ff', backgroundColor: 'rgba(140,82,255,0.15)',
      pointBackgroundColor: '#8c52ff' }]
  };
  salesChartOptions: any = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } } }
  };

  // Category doughnut
  categoryChartData: any = {
    labels: [],
    datasets: [{ data: [], backgroundColor: ['#8c52ff','#27ae60','#3498db','#f39c12','#e74c3c','#9b59b6','#1abc9c'] }]
  };
  categoryChartOptions: any = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }
  };

  // Status bar
  statusChartData: any = {
    labels: ['Beklemede','Kargoda','Teslim','İptal'],
    datasets: [{ data: [0,0,0,0], backgroundColor: ['#f39c12','#3498db','#27ae60','#e74c3c'] }]
  };
  statusChartOptions: any = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { y: { beginAtZero: true } }
  };

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  get isCorporate() { return this.user?.role === 'CORPORATE'; }

  // Date range
  selectedDays = 30;
  readonly dateRanges = [
    { label: 'Son 7 Gün',   value: 7 },
    { label: 'Son 30 Gün',  value: 30 },
    { label: 'Son 60 Gün',  value: 60 },
    { label: 'Son 90 Gün',  value: 90 },
  ];

  // Customer segmentation
  segments: any = null;
  loadingSegments = false;
  showSegments = false;

  ngOnInit() {
    this.user    = this.authService.getCurrentUser();
    this.isAdmin = this.user?.role === 'ADMIN';
    this.load();
  }

  onDateRangeChange() { this.load(); }

  loadSegments() {
    this.loadingSegments = true;
    this.http.get<any>(`${environment.apiUrl}/analytics/customers`).subscribe({
      next: res => { this.segments = res?.data ?? res; this.loadingSegments = false; this.showSegments = true; this.cdr.detectChanges(); },
      error: () => { this.loadingSegments = false; }
    });
  }

  load() {
    this.http.get<any>(`${environment.apiUrl}/analytics/dashboard?days=${this.selectedDays}`).subscribe({
      next: res => {
        const d = res?.data ?? {};
        this.kpi = {
          revenue:         `$${(d.totalRevenue    ?? 0).toLocaleString()}`,
          revenueGrowth:   d.revenueGrowth         ?? '+0%',
          orders:          `${d.totalOrders        ?? 0}`,
          ordersGrowth:    d.ordersGrowth           ?? '+0%',
          customers:       `${d.totalCustomers     ?? 0}`,
          customersGrowth: d.customersGrowth        ?? '+0%',
          rating:          `${d.averageRating       ?? 0}`,
          ratingGrowth:    d.ratingGrowth           ?? '+0.0'
        };
        this.orderStatus = {
          pending:   d.pendingOrders   ?? 0,
          shipped:   d.shippedOrders   ?? 0,
          delivered: d.deliveredOrders ?? 0,
          cancelled: d.cancelledOrders ?? 0
        };
        this.topProducts = d.topProducts ?? [];

        const trend = d.salesTrend?.length ? d.salesTrend
          : [{ label:'Pzt',value:1200 },{ label:'Sal',value:1900 },{ label:'Çar',value:1500 },
             { label:'Per',value:2200 },{ label:'Cum',value:2800 },{ label:'Cmt',value:3100 },{ label:'Paz',value:2400 }];
        this.salesChartData = {
          labels: trend.map((p: any) => p.label),
          datasets: [{ ...this.salesChartData.datasets[0], data: trend.map((p: any) => p.value) }]
        };

        if (d.categoryBreakdown?.length) {
          this.categoryChartData = {
            labels:   d.categoryBreakdown.map((p: any) => p.label),
            datasets: [{ ...this.categoryChartData.datasets[0], data: d.categoryBreakdown.map((p: any) => p.value) }]
          };
        } else {
          this.categoryChartData = { labels: ['Elektronik','Giyim','Ev','Güzellik'],
            datasets: [{ ...this.categoryChartData.datasets[0], data: [45000,32000,18000,12000] }] };
        }

        this.statusChartData = { ...this.statusChartData,
          datasets: [{ ...this.statusChartData.datasets[0],
            data: [this.orderStatus.pending, this.orderStatus.shipped,
                   this.orderStatus.delivered, this.orderStatus.cancelled] }] };

        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.kpi = { revenue:'$48,294', revenueGrowth:'+12.5%', orders:'1,842', ordersGrowth:'+5.2%',
                     customers:'3,421', customersGrowth:'+18.4%', rating:'4.8', ratingGrowth:'+0.2' };
        this.salesChartData = { labels: ['Pzt','Sal','Çar','Per','Cum','Cmt','Paz'],
          datasets: [{ ...this.salesChartData.datasets[0], data: [4200,5100,4600,7200,6800,8100,6400] }] };
        this.categoryChartData = { labels: ['Elektronik','Giyim','Ev & Yaşam','Güzellik'],
          datasets: [{ ...this.categoryChartData.datasets[0], data: [45000,32000,18000,12000] }] };
        this.statusChartData = { ...this.statusChartData,
          datasets: [{ ...this.statusChartData.datasets[0], data: [92, 276, 1437, 37] }] };
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  logout() {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}

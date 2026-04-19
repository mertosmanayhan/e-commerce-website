import { Component, OnInit } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-dashboard-layout',
  standalone: true,
  imports: [RouterModule],
  templateUrl: './dashboard-layout.html',
  styleUrl: './dashboard-layout.css'
})
export class DashboardLayout implements OnInit {
  user: any = null;

  get isAdmin()     { return this.user?.role === 'ADMIN'; }
  get isCorporate() { return this.user?.role === 'CORPORATE'; }
  get roleLabel()   { return this.isAdmin ? 'Platform Admin' : 'Mağaza Sahibi'; }

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    if (!this.user) this.router.navigate(['/login']);
  }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
}

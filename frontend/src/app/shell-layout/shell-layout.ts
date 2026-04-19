import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { AuthService } from '../auth.service';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-shell-layout',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './shell-layout.html',
  styleUrl: './shell-layout.css',
})
export class ShellLayout implements OnInit {
  user: any = null;
  sidebarOpen = true; // mobil toggle için

  constructor(
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {}

  get isAdmin()      { return this.user?.role === 'ADMIN'; }
  get isCorporate()  { return this.user?.role === 'CORPORATE'; }
  get isIndividual() { return this.user?.role === 'INDIVIDUAL'; }

  get roleLabel(): string {
    if (this.isAdmin)     return 'Admin';
    if (this.isCorporate) return 'Mağaza Sahibi';
    return 'Bireysel';
  }

  get isGuest() { return !this.user; }

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    // Navigasyon tamamlandığında kullanıcıyı yenile
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe(() => {
        this.user = this.authService.getCurrentUser();
        this.cdr.detectChanges();
      });
  }

  isActive(path: string): boolean {
    return this.router.url.startsWith('/' + path);
  }

  logout() {
    this.authService.logout();
  }

  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen;
  }
}

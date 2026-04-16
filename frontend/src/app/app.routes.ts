import { Routes } from '@angular/router';
import { authGuard, roleGuard } from './auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'products', pathMatch: 'full' },

  // Public routes — lazy loaded
  { path: 'login',           loadComponent: () => import('./login/login').then(m => m.Login) },
  { path: 'signup',          loadComponent: () => import('./signup/signup').then(m => m.Signup) },
  { path: 'forgot-password', loadComponent: () => import('./forgot-password/forgot-password.component').then(m => m.ForgotPasswordComponent) },
  { path: 'products',        loadComponent: () => import('./product-list/product-list').then(m => m.ProductList) },
  { path: 'product/:id',     loadComponent: () => import('./product-detail/product-detail').then(m => m.ProductDetail) },

  // Auth-only routes — lazy loaded
  { path: 'cart',      loadComponent: () => import('./cart/cart').then(m => m.CartComponent),    canActivate: [authGuard] },
  { path: 'checkout',  loadComponent: () => import('./checkout/checkout').then(m => m.Checkout), canActivate: [roleGuard(['INDIVIDUAL'])] },
  { path: 'orders',    loadComponent: () => import('./orders/orders').then(m => m.Orders),       canActivate: [authGuard] },
  { path: 'wishlist',  loadComponent: () => import('./wishlist/wishlist').then(m => m.Wishlist),  canActivate: [authGuard] },
  { path: 'profile',   loadComponent: () => import('./profile/profile').then(m => m.Profile),     canActivate: [authGuard] },
  { path: 'shipments',    loadComponent: () => import('./shipments/shipments').then(m => m.Shipments),           canActivate: [authGuard] },
  { path: 'reviews-page', loadComponent: () => import('./reviews-page/reviews-page').then(m => m.ReviewsPage),   canActivate: [authGuard] },
  { path: 'ai-assistant', loadComponent: () => import('./ai-assistant/ai-assistant').then(m => m.AiAssistant),   canActivate: [authGuard] },
  { path: 'customers',    loadComponent: () => import('./customers/customers').then(m => m.Customers),           canActivate: [roleGuard(['ADMIN'])] },
  { path: 'store-settings', loadComponent: () => import('./store-settings/store-settings').then(m => m.StoreSettings), canActivate: [roleGuard(['ADMIN', 'CORPORATE'])] },

  // Role-based routes — lazy loaded
  { path: 'dashboard', loadComponent: () => import('./dashboard/dashboard').then(m => m.Dashboard),      canActivate: [roleGuard(['CORPORATE', 'ADMIN'])] },
  { path: 'analytics', loadComponent: () => import('./analytics/analytics').then(m => m.AnalyticsPage),  canActivate: [roleGuard(['INDIVIDUAL'])] },
  { path: 'admin',     redirectTo: 'dashboard', pathMatch: 'full' },

  { path: '**', redirectTo: 'products' }
];

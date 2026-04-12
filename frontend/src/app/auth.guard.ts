import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/** Requires any authenticated user */
export const authGuard: CanActivateFn = () => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  if (!auth.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }
  return true;
};

/** Requires one of the given roles */
export const roleGuard = (roles: string[]): CanActivateFn => () => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  if (!auth.isAuthenticated()) {
    router.navigate(['/login']);
    return false;
  }
  const user = auth.getCurrentUser();
  if (user && roles.includes(user.role)) {
    return true;
  }
  // Redirect to the appropriate home page based on role
  const role = user?.role;
  if (role === 'CORPORATE' || role === 'ADMIN') {
    router.navigate(['/dashboard']);
  } else {
    router.navigate(['/products']);
  }
  return false;
};

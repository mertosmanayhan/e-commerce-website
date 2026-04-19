import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { AuthService } from './auth.service';

/** Requires any authenticated user */
export const authGuard: CanActivateFn = (_route: ActivatedRouteSnapshot, state: RouterStateSnapshot) => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  if (!auth.isAuthenticated()) {
    router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }
  return true;
};

/** Requires one of the given roles */
export const roleGuard = (roles: string[]): CanActivateFn => (_route: ActivatedRouteSnapshot, state: RouterStateSnapshot) => {
  const auth   = inject(AuthService);
  const router = inject(Router);
  if (!auth.isAuthenticated()) {
    router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }
  const user = auth.getCurrentUser();
  if (user && roles.includes(user.role)) {
    return true;
  }
  const role = user?.role;
  if (role === 'CORPORATE' || role === 'ADMIN') {
    router.navigate(['/dashboard']);
  } else {
    router.navigate(['/products']);
  }
  return false;
};

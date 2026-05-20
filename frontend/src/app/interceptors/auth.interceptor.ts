import { HttpInterceptorFn, HttpErrorResponse, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth';

/**
 * Interceptor de autentificare cu refresh automat.
 * Când un request returnează 401 (token expirat), încearcă să reînnoiască
 * access token-ul folosind refresh token-ul stocat.
 * Dacă refresh-ul reușește, request-ul original este reluat cu noul token.
 * Dacă refresh-ul eșuează, utilizatorul este delogat.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  // Nu interceptăm login/refresh pentru a evita bucle infinite
  if (req.url.includes('/auth/login') || req.url.includes('/auth/refresh')) {
    return next(req);
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401) {
        return throwError(() => error);
      }

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        authService.logout();
        return throwError(() => error);
      }

      // Încearcă refresh-ul token-ului
      return authService.refreshAccessToken(refreshToken).pipe(
        switchMap((response: any) => {
          const newToken = response.access_token;
          localStorage.setItem('access_token', newToken);

          // Reia request-ul original cu noul token
          const retryReq = req.clone({
            setHeaders: { Authorization: `Bearer ${newToken}` }
          });
          return next(retryReq);
        }),
        catchError((refreshError) => {
          // Refresh-ul a eșuat (refresh token expirat) → logout
          authService.logout();
          return throwError(() => refreshError);
        })
      );
    })
  );
};

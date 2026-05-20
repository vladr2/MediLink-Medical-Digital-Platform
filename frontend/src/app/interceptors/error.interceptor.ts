import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { NotificationService } from '../services/notification';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const notification = inject(NotificationService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // Nu afișa notificări pentru export GDPR sau alte blob-uri
      if (req.responseType === 'blob') {
        return throwError(() => error);
      }

      switch (error.status) {
        case 0:
          // Fără conexiune / server offline
          notification.error('Serverul nu răspunde. Verifică conexiunea.');
          break;

        case 401:
          // Gestionat de authInterceptor (refresh + retry)
          // Ajunge aici doar dacă refresh-ul a eșuat → authInterceptor face logout
          break;

        case 403:
          // Acces refuzat (rol insuficient) — lasă componenta să gestioneze
          // Nu afișăm notificare globală, să nu dublăm mesajele
          break;

        case 422:
          // Erori de validare Pydantic — lăsate la componenta care face requestul
          break;

        case 500:
        case 502:
        case 503:
          notification.error('Eroare internă de server. Încearcă din nou.');
          break;
      }

      return throwError(() => error);
    })
  );
};

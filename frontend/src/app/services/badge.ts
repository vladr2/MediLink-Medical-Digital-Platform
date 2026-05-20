import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from './api';

@Injectable({ providedIn: 'root' })
export class BadgeService {
  private pendingCount$ = new BehaviorSubject<number>(0);
  pending$ = this.pendingCount$.asObservable();

  constructor(private api: ApiService) {}

  /** Reîncarcă numărul de programări în așteptare (pentru doctor/admin). */
  refresh(): void {
    this.api.get<any[]>('/appointments/').subscribe({
      next: (appointments) => {
        const count = appointments.filter(a => a.status === 'pending').length;
        this.pendingCount$.next(count);
      },
      error: () => this.pendingCount$.next(0),
    });
  }

  reset(): void {
    this.pendingCount$.next(0);
  }
}

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { HttpHeaders } from '@angular/common/http';

export interface User {
  id: string;
  email: string;
  role: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  birth_date?: string;
  address?: string;
  email_notifications?: boolean;
  mfa_enabled?: boolean;
}

export function getFullName(user: User | null): string {
  if (!user) return '';
  if (user.first_name && user.last_name) return `${user.first_name} ${user.last_name}`;
  if (user.first_name) return user.first_name;
  if (user.last_name) return user.last_name;
  return user.email;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private baseUrl = '/api';
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    const token = localStorage.getItem('access_token');
    if (token) {
      this.loadCurrentUser();
    }
  }

  login(email: string, password: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/login`, { email, password }).pipe(
      tap(response => {
        if (!response.mfa_required) {
          localStorage.setItem('access_token', response.access_token);
          if (response.refresh_token) {
            localStorage.setItem('refresh_token', response.refresh_token);
          }
          this.loadCurrentUser();
        }
      })
    );
  }

  completeMfaLogin(mfaToken: string, code: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/mfa/verify`, {
      mfa_token: mfaToken,
      code,
    }).pipe(
      tap(response => {
        localStorage.setItem('access_token', response.access_token);
        if (response.refresh_token) {
          localStorage.setItem('refresh_token', response.refresh_token);
        }
        this.loadCurrentUser();
      })
    );
  }

  loadCurrentUser(): void {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    this.http.get<User>(`${this.baseUrl}/me`, {
      headers: { Authorization: `Bearer ${token}` }
    }).subscribe({
      next: user => this.currentUserSubject.next(user),
      error: () => this.logout()
    });
  }

  logout(): void {
    // Revocă sesiunea în DB (Feature 9) — best effort, nu blochează logout-ul local
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      this.http.post(`${this.baseUrl}/auth/logout`, { refresh_token: refreshToken })
        .subscribe({ error: () => {} });
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.currentUserSubject.next(null);
    this.router.navigate(['/authentication/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }

  refreshAccessToken(refreshToken: string): Observable<any> {
    return this.http.post<any>(
      `${this.baseUrl}/auth/refresh`,
      { refresh_token: refreshToken },
      { headers: new HttpHeaders({ 'Content-Type': 'application/json' }) }
    );
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  register(data: {
    email: string;
    password: string;
    role: string;
    first_name?: string;
    last_name?: string;
  }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/register`, data);
  }
}
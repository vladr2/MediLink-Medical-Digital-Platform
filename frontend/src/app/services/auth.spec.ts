import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { AuthService } from './auth';

describe('AuthService', () => {
  let service: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideRouter([]), AuthService],
    });
    service = TestBed.inject(AuthService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return null for currentUser initially (no token in localStorage)', () => {
    localStorage.removeItem('access_token');
    // fără token, BehaviorSubject pornește cu null
    let user: any = undefined;
    service.currentUser$.subscribe(u => (user = u));
    expect(user).toBeNull();
  });
});

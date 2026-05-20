import { FormControl, FormGroup, Validators } from '@angular/forms';
import { AppSideLoginComponent } from './side-login.component';
import { Subject, of, throwError } from 'rxjs';

/**
 * Testăm logica componentei direct (fără TestBed) pentru a evita
 * problemele de compilare ale template-ului în mediul Karma.
 */
describe('AppSideLoginComponent — logică business', () => {
  let component: AppSideLoginComponent;
  let authSpy: jasmine.SpyObj<any>;
  let routerSpy: jasmine.SpyObj<any>;

  beforeEach(() => {
    authSpy = jasmine.createSpyObj('AuthService', ['login', 'completeMfaLogin']);
    routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    component = new AppSideLoginComponent(routerSpy, authSpy);
  });

  // ── Stare inițială ────────────────────────────────────────────────────────

  it('should start on credentials step', () => {
    expect(component.step).toBe('credentials');
  });

  it('should have loading = false initially', () => {
    expect(component.loading).toBeFalse();
  });

  it('should have empty error message initially', () => {
    expect(component.errorMessage).toBe('');
  });

  it('should have an invalid form when empty', () => {
    expect(component.form.invalid).toBeTrue();
  });

  // ── Validare formular ─────────────────────────────────────────────────────

  it('should mark email as invalid for non-email string', () => {
    component.f['uname'].setValue('not-an-email');
    expect(component.f['uname'].invalid).toBeTrue();
  });

  it('should mark email as valid for correct format', () => {
    component.f['uname'].setValue('test@example.com');
    expect(component.f['uname'].valid).toBeTrue();
  });

  it('should require password to be non-empty', () => {
    component.f['password'].setValue('');
    expect(component.f['password'].invalid).toBeTrue();
  });

  it('should have a valid form with correct email + password', () => {
    component.f['uname'].setValue('user@test.com');
    component.f['password'].setValue('password123');
    expect(component.form.valid).toBeTrue();
  });

  // ── Comportament submit ───────────────────────────────────────────────────

  it('submit should NOT call authService.login when form is invalid', () => {
    component.submit();
    expect(authSpy.login).not.toHaveBeenCalled();
  });

  it('submit calls authService.login with correct credentials', (done) => {
    authSpy.login.and.returnValue(of({ access_token: 'tok', mfa_required: false }));
    component.f['uname'].setValue('user@test.com');
    component.f['password'].setValue('pass123');
    component.submit();
    setTimeout(() => {
      expect(authSpy.login).toHaveBeenCalledWith('user@test.com', 'pass123');
      done();
    }, 0);
  });

  it('submit transitions to MFA step when server returns mfa_required', (done) => {
    authSpy.login.and.returnValue(of({ mfa_required: true, mfa_token: 'mfa-tok-xyz' }));
    component.f['uname'].setValue('user@test.com');
    component.f['password'].setValue('pass123');
    component.submit();
    setTimeout(() => {
      expect(component.step).toBe('mfa');
      expect(component.mfaToken).toBe('mfa-tok-xyz');
      done();
    }, 0);
  });

  it('submit sets errorMessage on login failure', (done) => {
    authSpy.login.and.returnValue(
      throwError(() => ({ error: { detail: 'Email sau parolă incorectă' } }))
    );
    component.f['uname'].setValue('user@test.com');
    component.f['password'].setValue('wrong');
    component.submit();
    setTimeout(() => {
      expect(component.errorMessage).toBe('Email sau parolă incorectă');
      expect(component.loading).toBeFalse();
      done();
    }, 0);
  });

  // ── Pasul MFA ─────────────────────────────────────────────────────────────

  it('submitMfa should NOT call completeMfaLogin if code is too short', () => {
    component.step = 'mfa';
    component.mfaCode = '123'; // < 6 cifre
    component.submitMfa();
    expect(authSpy.completeMfaLogin).not.toHaveBeenCalled();
  });

  it('submitMfa should NOT call completeMfaLogin if code is empty', () => {
    component.step = 'mfa';
    component.mfaCode = '';
    component.submitMfa();
    expect(authSpy.completeMfaLogin).not.toHaveBeenCalled();
  });

  it('backToCredentials resets step and MFA fields', () => {
    component.step = 'mfa';
    component.mfaToken = 'some-token';
    component.mfaCode = '123456';
    component.errorMessage = 'Eroare';
    component.backToCredentials();
    expect(component.step).toBe('credentials');
    expect(component.mfaToken).toBe('');
    expect(component.mfaCode).toBe('');
    expect(component.errorMessage).toBe('');
  });
});

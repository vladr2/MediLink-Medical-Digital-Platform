import { Component } from '@angular/core';
import { FormGroup, FormControl, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MaterialModule } from 'src/app/material.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from 'src/app/services/auth';
import { TablerIconsModule } from 'angular-tabler-icons';

@Component({
  selector: 'app-side-login',
  imports: [RouterModule, MaterialModule, FormsModule, ReactiveFormsModule, CommonModule, TablerIconsModule],
  templateUrl: './side-login.component.html',
})
export class AppSideLoginComponent {
  loading      = false;
  errorMessage = '';

  // ── MFA step ──────────────────────────────────────────────────────────────
  step: 'credentials' | 'mfa' = 'credentials';
  mfaToken   = '';
  mfaCode    = '';

  constructor(private router: Router, private authService: AuthService) {}

  form = new FormGroup({
    uname:    new FormControl('', [Validators.required, Validators.email]),
    password: new FormControl('', [Validators.required]),
  });

  get f() { return this.form.controls; }

  submit() {
    if (this.form.invalid) return;
    this.loading = true;
    this.errorMessage = '';

    this.authService.login(
      this.f['uname'].value!,
      this.f['password'].value!
    ).subscribe({
      next: (res: any) => {
        this.loading = false;
        if (res.mfa_required) {
          this.mfaToken = res.mfa_token;
          this.step = 'mfa';
        } else {
          this.router.navigate(['/dashboard']);
        }
      },
      error: (err: any) => {
        this.loading = false;
        this.errorMessage = err.error?.detail || 'Email sau parolă incorectă';
      }
    });
  }

  submitMfa() {
    if (!this.mfaCode || this.mfaCode.length !== 6) return;
    this.loading = true;
    this.errorMessage = '';

    this.authService.completeMfaLogin(this.mfaToken, this.mfaCode).subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/dashboard']);
      },
      error: (err: any) => {
        this.loading = false;
        this.mfaCode = '';
        this.errorMessage = err.error?.detail || 'Cod incorect. Încearcă din nou.';
      }
    });
  }

  backToCredentials() {
    this.step = 'credentials';
    this.mfaToken = '';
    this.mfaCode = '';
    this.errorMessage = '';
  }
}

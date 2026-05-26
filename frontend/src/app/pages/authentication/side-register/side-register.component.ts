import { Component } from '@angular/core';
import { AbstractControl, FormGroup, FormControl, Validators, ValidationErrors } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { MaterialModule } from 'src/app/material.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from 'src/app/services/auth';
import { TablerIconsModule } from 'angular-tabler-icons';

function passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
  const value: string = control.value || '';
  if (!value) return null;
  if (value.length < 8) return { tooShort: true };
  if (!/[A-Z]/.test(value)) return { noUppercase: true };
  if (!/\d/.test(value)) return { noDigit: true };
  return null;
}

@Component({
  selector: 'app-side-register',
  standalone: true,
  imports: [RouterModule, MaterialModule, FormsModule, ReactiveFormsModule, CommonModule, TablerIconsModule],
  templateUrl: './side-register.component.html',
})
export class AppSideRegisterComponent {
  loading = false;
  errorMessage = '';
  successMessage = '';
  hidePassword = true;

  constructor(private router: Router, private authService: AuthService) {}

  form = new FormGroup({
    first_name: new FormControl('', [Validators.required]),
    last_name:  new FormControl('', [Validators.required]),
    email:      new FormControl('', [Validators.required, Validators.email]),
    password:   new FormControl('', [Validators.required, passwordStrengthValidator]),
    role:       new FormControl('patient', [Validators.required]),
  });

  get f() { return this.form.controls; }

  get passwordErrors() {
    const ctrl = this.f['password'];
    if (!ctrl.value || !ctrl.dirty) return null;
    return ctrl.errors;
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const { first_name, last_name, email, password, role } = this.form.value;

    this.authService.register({ first_name: first_name!, last_name: last_name!, email: email!, password: password!, role: role! }).subscribe({
      next: () => {
        this.loading = false;
        this.successMessage = 'Cont creat cu succes! Te poți autentifica acum.';
        setTimeout(() => this.router.navigate(['/authentication/login']), 2000);
      },
      error: (err: any) => {
        this.loading = false;
        const detail = err.error?.detail;
        if (detail === 'Email already registered') {
          this.errorMessage = 'Această adresă de email este deja înregistrată.';
        } else if (Array.isArray(detail)) {
          this.errorMessage = detail.map((e: any) => e.msg).join(', ');
        } else {
          this.errorMessage = detail || 'A apărut o eroare. Încearcă din nou.';
        }
      }
    });
  }
}

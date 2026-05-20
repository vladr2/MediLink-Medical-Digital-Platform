import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, AbstractControl } from '@angular/forms';
import { Router } from '@angular/router';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { MatStepper } from '@angular/material/stepper';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { NotificationService } from '../../services/notification';

// ── Validators ────────────────────────────────────────────────────────────────

function phoneValidator(control: AbstractControl) {
  const v = control.value;
  if (!v || v === '') return null;
  return /^[\d\s\+\-\(\)]{7,20}$/.test(v) ? null : { phoneInvalid: true };
}

function cnpValidator(control: AbstractControl) {
  const v = control.value;
  if (!v || v === '') return null;
  return /^\d{13}$/.test(v) ? null : { cnpInvalid: true };
}

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, ReactiveFormsModule],
  templateUrl: './onboarding.html',
})
export class OnboardingComponent implements OnInit {
  @ViewChild('stepper') stepper!: MatStepper;

  personalForm: FormGroup;
  medicalForm: FormGroup;

  savingPersonal = false;
  savingMedical = false;

  patientProfileId: string | null = null;

  bloodTypes = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

  constructor(
    private fb: FormBuilder,
    private apiService: ApiService,
    private authService: AuthService,
    private notification: NotificationService,
    private router: Router,
  ) {
    this.personalForm = this.fb.group({
      first_name: [''],
      last_name: [''],
      phone: ['', phoneValidator],
      birth_date: [''],
      address: [''],
    });

    this.medicalForm = this.fb.group({
      blood_type: [''],
      gender: [''],
      cnp: ['', cnpValidator],
      allergies: [''],
      chronic_conditions: [''],
      emergency_contact: [''],
      emergency_phone: ['', phoneValidator],
    });
  }

  ngOnInit(): void {
    // Pre-fill personal data if already partially set
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.personalForm.patchValue({
          first_name: user.first_name || '',
          last_name: user.last_name || '',
          phone: (user as any).phone || '',
          birth_date: (user as any).birth_date || '',
          address: (user as any).address || '',
        });
      }
    });

    // Load existing patient profile for step 2
    this.apiService.get<any>('/patients/me').subscribe({
      next: (p) => {
        this.patientProfileId = p.id;
        this.medicalForm.patchValue({
          blood_type: p.blood_type || '',
          gender: p.gender || '',
          cnp: p.cnp || '',
          allergies: p.allergies || '',
          chronic_conditions: p.chronic_conditions || '',
          emergency_contact: p.emergency_contact || '',
          emergency_phone: p.emergency_phone || '',
        });
      },
      error: () => {}
    });
  }

  // ── Step 1 ─────────────────────────────────────────────────────────────────

  savePersonal(): void {
    if (this.personalForm.invalid) {
      this.personalForm.markAllAsTouched();
      return;
    }
    this.savingPersonal = true;
    this.apiService.put<any>('/me', this.personalForm.value).subscribe({
      next: () => {
        this.authService.loadCurrentUser();
        this.savingPersonal = false;
        this.stepper.next();
      },
      error: () => {
        this.savingPersonal = false;
        this.notification.error('Eroare la salvarea datelor personale.');
      }
    });
  }

  skipPersonal(): void {
    this.stepper.next();
  }

  // ── Step 2 ─────────────────────────────────────────────────────────────────

  saveMedical(): void {
    if (this.medicalForm.invalid) {
      this.medicalForm.markAllAsTouched();
      return;
    }
    if (!this.patientProfileId) {
      // No patient profile yet — skip silently
      this.stepper.next();
      return;
    }
    this.savingMedical = true;
    this.apiService.put<any>(`/patients/${this.patientProfileId}`, this.medicalForm.value).subscribe({
      next: () => {
        this.savingMedical = false;
        this.stepper.next();
      },
      error: (err) => {
        this.savingMedical = false;
        const detail = err?.error?.detail;
        const msg = Array.isArray(detail)
          ? detail.map((e: any) => e.msg).join(', ')
          : (typeof detail === 'string' ? detail : 'Eroare la salvarea datelor medicale.');
        this.notification.error(msg);
      }
    });
  }

  skipMedical(): void {
    this.stepper.next();
  }

  // ── Step 3 / Finish ────────────────────────────────────────────────────────

  private markDone(): void {
    const user = this.authService.getCurrentUser();
    if (user) {
      localStorage.setItem(`medilink_onboarding_${user.id}`, 'done');
    }
  }

  goToAppointments(): void {
    this.markDone();
    this.router.navigate(['/dashboard/appointments']);
  }

  goToDashboard(): void {
    this.markDone();
    this.router.navigate(['/dashboard']);
  }
}

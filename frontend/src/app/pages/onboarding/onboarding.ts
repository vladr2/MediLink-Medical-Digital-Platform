import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, AbstractControl } from '@angular/forms';
import { Router } from '@angular/router';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { MatStepper } from '@angular/material/stepper';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DATE_FORMATS, MAT_DATE_LOCALE, DateAdapter } from '@angular/material/core';
import { MomentDateAdapter, MAT_MOMENT_DATE_ADAPTER_OPTIONS } from '@angular/material-moment-adapter';
import moment from 'moment';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { NotificationService } from '../../services/notification';

const MY_DATE_FORMATS = {
  parse: { dateInput: 'DD/MM/YYYY' },
  display: {
    dateInput: 'DD/MM/YYYY',
    monthYearLabel: 'MMM YYYY',
    dateA11yLabel: 'DD/MM/YYYY',
    monthYearA11yLabel: 'MMMM YYYY',
  }
};

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
  imports: [CommonModule, MaterialModule, TablerIconsModule, ReactiveFormsModule, MatDatepickerModule],
  templateUrl: './onboarding.html',
  providers: [
    { provide: MAT_DATE_LOCALE, useValue: 'ro-RO' },
    { provide: DateAdapter, useClass: MomentDateAdapter, deps: [MAT_DATE_LOCALE, MAT_MOMENT_DATE_ADAPTER_OPTIONS] },
    { provide: MAT_DATE_FORMATS, useValue: MY_DATE_FORMATS },
  ],
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
      birth_date_moment: [null],
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
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.personalForm.patchValue({
          first_name: user.first_name || '',
          last_name: user.last_name || '',
          phone: (user as any).phone || '',
          address: (user as any).address || '',
          birth_date_moment: (user as any).birth_date
            ? moment((user as any).birth_date, ['DD/MM/YYYY', 'YYYY-MM-DD'])
            : null,
        });
      }
    });

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

    const raw = this.personalForm.value;
    const payload: any = {
      first_name: raw.first_name,
      last_name: raw.last_name,
      phone: raw.phone,
      address: raw.address,
    };
    if (raw.birth_date_moment && moment.isMoment(raw.birth_date_moment)) {
      payload.birth_date = raw.birth_date_moment.format('DD/MM/YYYY');
    }

    this.apiService.put<any>('/me', payload).subscribe({
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

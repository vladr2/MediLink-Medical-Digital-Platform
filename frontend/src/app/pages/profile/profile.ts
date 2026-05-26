import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DATE_FORMATS, MAT_DATE_LOCALE, DateAdapter } from '@angular/material/core';
import { MomentDateAdapter, MAT_MOMENT_DATE_ADAPTER_OPTIONS } from '@angular/material-moment-adapter';
import moment from 'moment';
import { ApiService } from '../../services/api';
import { AuthService, User } from '../../services/auth';
import { NotificationService } from '../../services/notification';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

const MY_DATE_FORMATS = {
  parse: { dateInput: 'DD/MM/YYYY' },
  display: {
    dateInput: 'DD/MM/YYYY',
    monthYearLabel: 'MMM YYYY',
    dateA11yLabel: 'DD/MM/YYYY',
    monthYearA11yLabel: 'MMMM YYYY',
  }
};

// Validator custom: CNP = exact 13 cifre
function cnpValidator(control: AbstractControl) {
  const v = control.value;
  if (!v || v === '') return null; // opțional
  return /^\d{13}$/.test(v) ? null : { cnpInvalid: true };
}

// Validator custom: telefon (7-20 caractere: cifre, spații, +, -, paranteze)
function phoneValidator(control: AbstractControl) {
  const v = control.value;
  if (!v || v === '') return null; // opțional
  return /^[\d\s\+\-\(\)]{7,20}$/.test(v) ? null : { phoneInvalid: true };
}

interface PatientProfile {
  id: string;
  user_id: string;
  blood_type: string;
  allergies: string;
  chronic_conditions: string;
  emergency_contact: string;
  emergency_phone: string;
  cnp: string;
  gender: string;
}

interface DoctorProfile {
  id: string;
  specialization: string;
  license_number: string;
  department: string;
  bio: string;
  phone_cabinet: string;
  schedule: string;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, ReactiveFormsModule, SkeletonComponent, MatDatepickerModule],
  templateUrl: './profile.html',
  providers: [
    { provide: MAT_DATE_LOCALE, useValue: 'ro-RO' },
    { provide: DateAdapter, useClass: MomentDateAdapter, deps: [MAT_DATE_LOCALE, MAT_MOMENT_DATE_ADAPTER_OPTIONS] },
    { provide: MAT_DATE_FORMATS, useValue: MY_DATE_FORMATS },
  ],
})
export class ProfileComponent implements OnInit {
  currentUser: User | null = null;
  patientProfile: PatientProfile | null = null;
  doctorProfile: DoctorProfile | null = null;
  userForm: FormGroup;
  patientForm: FormGroup;
  doctorForm: FormGroup;
  loading = true;
  saving = false;
  successMessage = '';
  errorMessage = '';

  bloodTypes = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

  exportingGdpr = false;
  exportingPdf = false;
  changingPassword = false;
  passwordForm: FormGroup;
  emailNotifications = true;
  savingEmailPref = false;

  // ── 2FA ───────────────────────────────────────────────────────────────────
  mfaEnabled      = false;
  showMfaSetup    = false;
  mfaSecret       = '';
  mfaQrUri        = '';
  mfaSetupCode    = '';
  mfaDisableCode  = '';
  showMfaDisable  = false;
  savingMfa       = false;

  // ── Feature 9: Sesiuni active ─────────────────────────────────────────────
  sessions: any[] = [];
  loadingSessions = false;
  revokingSession: string | null = null;
  revokingAll = false;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private fb: FormBuilder,
    private notification: NotificationService,
  ) {
    this.userForm = this.fb.group({
      first_name: [''],
      last_name: [''],
      phone: ['', phoneValidator],
      birth_date_moment: [null],
      address: [''],
    });

    this.patientForm = this.fb.group({
      blood_type: [''],
      allergies: [''],
      chronic_conditions: [''],
      emergency_contact: [''],
      emergency_phone: ['', phoneValidator],
      cnp: ['', cnpValidator],
      gender: [''],
    });

    this.doctorForm = this.fb.group({
      specialization: [''],
      license_number: [''],
      department: [''],
      bio: [''],
      phone_cabinet: [''],
      schedule: [''],
    });

    this.passwordForm = this.fb.group({
      current_password: ['', Validators.required],
      new_password: ['', [
        Validators.required,
        Validators.minLength(8),
        Validators.pattern(/^(?=.*[A-Z])(?=.*\d).+$/),
      ]],
      confirm_password: ['', Validators.required],
    }, { validators: this.passwordMatchValidator });
  }

  passwordMatchValidator(group: AbstractControl) {
    const np = group.get('new_password')?.value;
    const cp = group.get('confirm_password')?.value;
    return np === cp ? null : { passwordMismatch: true };
  }

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user) {
        this.emailNotifications = user.email_notifications !== false;
        this.mfaEnabled = user?.mfa_enabled ?? false;
        this.userForm.patchValue({
          first_name: user.first_name || '',
          last_name: user.last_name || '',
          phone: user.phone || '',
          address: user.address || '',
          birth_date_moment: user.birth_date
            ? moment(user.birth_date, ['DD/MM/YYYY', 'YYYY-MM-DD'])
            : null,
        });
        if (user.role === 'patient' && !this.patientProfile) {
          this.loadPatientProfile();
        } else if (user.role === 'doctor' && !this.doctorProfile) {
          this.loadDoctorProfile();
        } else {
          this.loading = false;
        }
      }
    });
    this.loadSessions();
  }

  loadPatientProfile(): void {
    this.apiService.get<PatientProfile>('/patients/me').subscribe({
      next: (profile) => {
        this.patientProfile = profile;
        this.patientForm.patchValue({
          blood_type: profile.blood_type || '',
          allergies: profile.allergies || '',
          chronic_conditions: profile.chronic_conditions || '',
          emergency_contact: profile.emergency_contact || '',
          emergency_phone: profile.emergency_phone || '',
          cnp: profile.cnp || '',
          gender: profile.gender || '',
        });
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  loadDoctorProfile(): void {
    this.apiService.get<DoctorProfile>('/doctors/me').subscribe({
      next: (profile) => {
        this.doctorProfile = profile;
        this.doctorForm.patchValue({
          specialization: profile.specialization || '',
          license_number: profile.license_number || '',
          department: profile.department || '',
          bio: profile.bio || '',
          phone_cabinet: profile.phone_cabinet || '',
          schedule: profile.schedule || '',
        });
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  saveUserInfo(): void {
    if (this.userForm.invalid) {
      this.userForm.markAllAsTouched();
      return;
    }
    this.saving = true;
    const raw = this.userForm.value;
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
        this.saving = false;
        this.notification.success('Profil actualizat cu succes!');
      },
      error: () => {
        this.saving = false;
        this.notification.error('Eroare la salvarea profilului.');
      }
    });
  }

  savePatientInfo(): void {
    if (!this.patientProfile) return;
    if (this.patientForm.invalid) {
      this.patientForm.markAllAsTouched();
      return;
    }
    this.saving = true;
    this.apiService.put<PatientProfile>(`/patients/${this.patientProfile.id}`, this.patientForm.value).subscribe({
      next: () => {
        this.saving = false;
        this.notification.success('Date medicale actualizate cu succes!');
      },
      error: (err) => {
        this.saving = false;
        const detail = err?.error?.detail;
        let msg = 'Eroare la salvarea datelor medicale.';
        if (Array.isArray(detail)) {
          // Erori de validare Pydantic — array cu obiecte {loc, msg, type}
          msg = detail.map((e: any) => e.msg).join(', ');
        } else if (typeof detail === 'string') {
          msg = detail;
        }
        this.notification.error(msg);
      }
    });
  }

  saveDoctorInfo(): void {
    this.saving = true;
    this.apiService.put<DoctorProfile>('/doctors/me', this.doctorForm.value).subscribe({
      next: () => {
        this.saving = false;
        this.notification.success('Profil medical actualizat cu succes!');
      },
      error: () => {
        this.saving = false;
        this.notification.error('Eroare la salvarea profilului medical.');
      }
    });
  }

  changePassword(): void {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }
    this.changingPassword = true;
    const { current_password, new_password } = this.passwordForm.value;
    this.apiService.post<any>('/auth/change-password', { current_password, new_password }).subscribe({
      next: () => {
        this.changingPassword = false;
        this.passwordForm.reset();
        this.notification.success('Parola a fost schimbată cu succes!');
      },
      error: (err) => {
        this.changingPassword = false;
        const msg = err?.error?.detail || 'Eroare la schimbarea parolei.';
        this.notification.error(msg);
      }
    });
  }

  toggleEmailNotifications(): void {
    this.emailNotifications = !this.emailNotifications;
    this.savingEmailPref = true;
    this.apiService.put<any>('/me', { email_notifications: this.emailNotifications }).subscribe({
      next: () => {
        this.authService.loadCurrentUser();
        this.savingEmailPref = false;
        const msg = this.emailNotifications
          ? 'Notificările email au fost activate.'
          : 'Notificările email au fost dezactivate.';
        this.notification.success(msg);
      },
      error: () => {
        // Revert on error
        this.emailNotifications = !this.emailNotifications;
        this.savingEmailPref = false;
        this.notification.error('Eroare la salvarea preferinței.');
      }
    });
  }

  // ── Feature 9: Sesiuni active ─────────────────────────────────────────────

  loadSessions(): void {
    this.loadingSessions = true;
    this.apiService.get<any[]>('/auth/sessions').subscribe({
      next: (data) => {
        this.sessions = data;
        this.loadingSessions = false;
      },
      error: () => { this.loadingSessions = false; }
    });
  }

  revokeSession(sessionId: string): void {
    this.revokingSession = sessionId;
    this.apiService.delete<any>(`/auth/sessions/${sessionId}`).subscribe({
      next: () => {
        this.sessions = this.sessions.filter(s => s.id !== sessionId);
        this.revokingSession = null;
        this.notification.success('Sesiune deconectată.');
      },
      error: () => {
        this.revokingSession = null;
        this.notification.error('Eroare la deconectarea sesiunii.');
      }
    });
  }

  revokeAllOtherSessions(): void {
    this.revokingAll = true;
    this.apiService.delete<any>('/auth/sessions').subscribe({
      next: (res) => {
        this.revokingAll = false;
        this.loadSessions(); // reîncarcă lista
        const count = res?.message?.match(/\d+/)?.[0] || '0';
        this.notification.success(`${count} sesiune(i) deconectată(e).`);
      },
      error: () => {
        this.revokingAll = false;
        this.notification.error('Eroare la deconectarea sesiunilor.');
      }
    });
  }

  exportAsPdf(): void {
    this.exportingPdf = true;
    const token = localStorage.getItem('access_token');
    fetch(`/api/patients/me/export?format=pdf`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => {
      if (!res.ok) throw new Error('Export failed');
      return res.blob();
    })
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const win = window.open(url, '_blank');
      if (!win) {
        this.notification.error('Permite pop-up-urile pentru a descărca PDF-ul.');
      }
      setTimeout(() => URL.revokeObjectURL(url), 120000);
    })
    .catch(() => this.notification.error('Eroare la generarea PDF-ului.'))
    .finally(() => { this.exportingPdf = false; });
  }

  exportGdprData(format: 'html' | 'json' = 'html'): void {
    this.exportingGdpr = true;
    const token = localStorage.getItem('access_token');
    const ext = format === 'json' ? 'json' : 'html';
    fetch(`/api/patients/me/export?format=${format}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => {
      if (!res.ok) throw new Error('Export failed');
      return res.blob();
    })
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `medilink_date_personale_${new Date().toISOString().split('T')[0]}.${ext}`;
      a.click();
      window.URL.revokeObjectURL(url);
      this.notification.success('Date exportate cu succes! (GDPR Art. 20)');
    })
    .catch(() => this.notification.error('Eroare la exportul datelor.'))
    .finally(() => { this.exportingGdpr = false; });
  }

  encodeUri(uri: string): string {
    return encodeURIComponent(uri);
  }

  setupMfa(): void {
    this.savingMfa = true;
    this.apiService.post<any>('/auth/mfa/setup', {}).subscribe({
      next: (res) => {
        this.mfaSecret  = res.secret;
        this.mfaQrUri   = res.qr_uri;
        this.showMfaSetup = true;
        this.savingMfa  = false;
      },
      error: () => { this.savingMfa = false; },
    });
  }

  enableMfa(): void {
    if (!this.mfaSetupCode || this.mfaSetupCode.length !== 6) return;
    this.savingMfa = true;
    this.apiService.post<any>('/auth/mfa/enable-confirm', {
      secret: this.mfaSecret,
      code: this.mfaSetupCode,
    }).subscribe({
      next: () => {
        this.mfaEnabled   = true;
        this.showMfaSetup = false;
        this.mfaSetupCode = '';
        this.mfaSecret    = '';
        this.savingMfa    = false;
        this.notification.success('2FA activat cu succes!');
      },
      error: (err: any) => {
        this.savingMfa = false;
        this.notification.error(err.error?.detail || 'Cod incorect');
      },
    });
  }

  disableMfa(): void {
    if (!this.mfaDisableCode || this.mfaDisableCode.length !== 6) return;
    this.savingMfa = true;
    this.apiService.post<any>('/auth/mfa/disable', { code: this.mfaDisableCode }).subscribe({
      next: () => {
        this.mfaEnabled      = false;
        this.showMfaDisable  = false;
        this.mfaDisableCode  = '';
        this.savingMfa       = false;
        this.notification.success('2FA dezactivat.');
      },
      error: (err: any) => {
        this.savingMfa = false;
        this.notification.error(err.error?.detail || 'Cod incorect');
      },
    });
  }
}
import { Component, OnInit, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { NotificationService } from '../../services/notification';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { MatDialog, MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';

// ── Dialog atribuire doctor ────────────────────────────────────────────────
import { Component as Comp } from '@angular/core';

@Comp({
  selector: 'app-assign-doctor-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule],
  template: `
    <div style="padding:24px;min-width:340px;">
      <h3 style="margin:0 0 6px;font-size:1rem;font-weight:700;color:#1e293b;">Atribuie doctor</h3>
      <p style="margin:0 0 18px;font-size:.82rem;color:#64748b;">
        Pacient: <strong>{{ data.patientName }}</strong>
      </p>
      <mat-form-field appearance="outline" class="w-100">
        <mat-label>Selectează doctor</mat-label>
        <mat-select [(ngModel)]="selectedDoctorId">
          <mat-option *ngFor="let d of data.doctors" [value]="d.id">
            Dr. {{ d.first_name }} {{ d.last_name }}
            <span style="font-size:.75rem;color:#94a3b8;"> · {{ d.specialization }}</span>
          </mat-option>
        </mat-select>
      </mat-form-field>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:8px;">
        <button mat-stroked-button (click)="dialogRef.close()">Anulează</button>
        <button mat-flat-button color="primary"
                [disabled]="!selectedDoctorId"
                (click)="dialogRef.close(selectedDoctorId)">
          Atribuie
        </button>
      </div>
    </div>
  `,
})
export class AssignDoctorDialogComponent {
  selectedDoctorId: string | null = null;
  constructor(
    public dialogRef: MatDialogRef<AssignDoctorDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { patientName: string; doctors: any[] },
  ) {}
}

// ── Main component ─────────────────────────────────────────────────────────

interface Patient {
  id: string;
  user_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  blood_type: string;
  allergies: string;
  chronic_conditions: string;
}

interface Doctor {
  id: string;
  user_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  specialization: string;
}

@Component({
  selector: 'app-assistant-patients',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, SkeletonComponent, MatDialogModule],
  templateUrl: './assistant-patients.html',
})
export class AssistantPatientsComponent implements OnInit {
  patients: Patient[] = [];
  filteredPatients: Patient[] = [];
  doctors: Doctor[] = [];

  loading = true;
  assigning: Record<string, boolean> = {};
  searchText = '';

  displayedColumns = ['full_name', 'blood_type', 'allergies', 'chronic', 'actions'];

  constructor(
    private apiService: ApiService,
    private notification: NotificationService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.apiService.get<Patient[]>('/patients/').subscribe({
      next: (data) => {
        this.patients = data;
        this.filteredPatients = data;
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
    this.apiService.get<Doctor[]>('/doctors/').subscribe({
      next: (data) => { this.doctors = data; },
      error: () => {},
    });
  }

  filterPatients(): void {
    const q = this.searchText.trim().toLowerCase();
    this.filteredPatients = q
      ? this.patients.filter(p =>
          `${p.first_name || ''} ${p.last_name || ''} ${p.email}`.toLowerCase().includes(q)
        )
      : this.patients;
  }

  patientName(p: Patient): string {
    const n = `${p.first_name || ''} ${p.last_name || ''}`.trim();
    return n || p.email;
  }

  openAssignDialog(patient: Patient): void {
    const ref = this.dialog.open(AssignDoctorDialogComponent, {
      width: '400px',
      data: { patientName: this.patientName(patient), doctors: this.doctors },
    });
    ref.afterClosed().subscribe((doctorId: string | undefined) => {
      if (!doctorId) return;
      this.assignDoctor(patient, doctorId);
    });
  }

  private assignDoctor(patient: Patient, doctorId: string): void {
    this.assigning[patient.id] = true;
    this.apiService.post(`/doctors/assign-patient/${patient.id}?doctor_id=${doctorId}`, {}).subscribe({
      next: () => {
        this.assigning[patient.id] = false;
        const doc = this.doctors.find(d => d.id === doctorId);
        const docName = doc ? `Dr. ${doc.first_name || ''} ${doc.last_name || ''}`.trim() : 'doctor';
        this.notification.success(`${this.patientName(patient)} atribuit la ${docName}.`);
      },
      error: (err) => {
        this.assigning[patient.id] = false;
        const msg = err?.error?.detail || 'Eroare la atribuire.';
        this.notification.error(msg);
      },
    });
  }
}

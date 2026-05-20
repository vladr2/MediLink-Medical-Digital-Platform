import { Component, OnInit, AfterViewChecked, ViewChild, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { NotificationService } from '../../services/notification';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { RecordDetailDialogComponent } from './record-detail-dialog.component';
import { ConfirmDialogComponent } from '../../components/confirm-dialog/confirm-dialog.component';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

// ── Dialog predicție risc ─────────────────────────────────────────────────
@Component({
  selector: 'app-risk-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule],
  template: `
    <div style="padding:24px;max-width:540px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:52px;height:52px;border-radius:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0;"
               [style.background]="bgColor">
            <span style="font-size:1.5rem;font-weight:900;" [style.color]="fgColor">
              {{ data.risk_score }}/10
            </span>
          </div>
          <div>
            <p style="margin:0;font-size:1rem;font-weight:700;color:#1e293b;">🧠 Predicție Risc AI</p>
            <p style="margin:0;font-size:.78rem;color:#64748b;">
              {{ levelLabel }} — {{ data.generated_at | date:'d MMM yyyy, HH:mm' }}
            </p>
          </div>
        </div>
        <button mat-icon-button (click)="close()">
          <i-tabler name="x" style="width:18px;height:18px;color:#64748b;"></i-tabler>
        </button>
      </div>

      <!-- Sumar -->
      <p style="margin:0 0 14px;font-size:.85rem;color:#374151;background:#f1f5f9;border-radius:8px;padding:10px 14px;line-height:1.6;">
        {{ data.summary }}
      </p>

      <!-- Factori -->
      <div style="margin-bottom:14px;" *ngIf="data.main_factors?.length > 0">
        <p style="margin:0 0 8px;font-size:.72rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px;">
          Factori de risc identificați
        </p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">
          <span *ngFor="let f of data.main_factors"
                style="background:#fff;border:1px solid #e2e8f0;border-radius:20px;padding:3px 10px;font-size:.76rem;color:#374151;">
            ⚠️ {{ f }}
          </span>
        </div>
      </div>

      <!-- Recomandări -->
      <div *ngIf="data.recommendations?.length > 0" style="margin-bottom:14px;">
        <p style="margin:0 0 8px;font-size:.72rem;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.5px;">
          Recomandări
        </p>
        <ul style="margin:0;padding-left:18px;">
          <li *ngFor="let r of data.recommendations"
              style="font-size:.82rem;color:#374151;margin-bottom:4px;line-height:1.5;">
            {{ r }}
          </li>
        </ul>
      </div>

      <p style="margin:0;font-size:.68rem;color:#94a3b8;font-style:italic;border-top:1px solid #f1f5f9;padding-top:10px;">
        ⚠️ Acest scor este generat de AI și nu înlocuiește evaluarea clinică a medicului.
      </p>
    </div>
  `,
})
export class RiskDialogComponent {
  constructor(
    private dialogRef: MatDialogRef<RiskDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
  ) {}

  get fgColor(): string {
    const m: Record<string, string> = { critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#22c55e' };
    return m[this.data.risk_level] ?? '#64748b';
  }
  get bgColor(): string {
    const m: Record<string, string> = { critical: '#fef2f2', high: '#fff7ed', medium: '#fffbeb', low: '#f0fdf4' };
    return m[this.data.risk_level] ?? '#f8fafc';
  }
  get levelLabel(): string {
    const m: Record<string, string> = { critical: '🔴 Risc Critic', high: '🟠 Risc Ridicat', medium: '🟡 Risc Mediu', low: '🟢 Risc Scăzut' };
    return m[this.data.risk_level] ?? 'Risc Necunoscut';
  }
  close() { this.dialogRef.close(); }
}

interface Patient {
  id: string;
  user_id?: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

interface MedicalRecord {
  id: string;
  patient_id: string;
  record_type: string;
  notes_encrypted: string;
  diagnosis: string;
  treatment: string;
  created_at: string;
  analysis_result: string;
}

@Component({
  selector: 'app-doctor-medical-records',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, FormsModule, ReactiveFormsModule, MatDialogModule, MatPaginatorModule, MatTableModule, SkeletonComponent],
  templateUrl: './doctor-medical-records.html',
})
export class DoctorMedicalRecordsComponent implements OnInit, AfterViewChecked {
  @ViewChild(MatPaginator) paginator!: MatPaginator;

  patients: Patient[] = [];
  dataSource = new MatTableDataSource<MedicalRecord>([]);
  selectedPatient: Patient | null = null;
  loading = false;
  saving = false;
  showForm = false;
  successMessage = '';
  errorMessage = '';
  displayedColumns = ['date', 'type', 'notes', 'diagnosis', 'actions'];

  recordTypes = ['consultatie', 'analiza', 'tratament', 'reteta', 'investigatie'];
  generatingReport = false;

  loadingRisk = false;
  private paginatorConnected = false;

  // ── Paginare ──────────────────────────────────────────────────────────────
  pageSize = 10;
  pageIndex = 0;

  get pagedRecords(): MedicalRecord[] {
    const data = this.dataSource.filteredData;
    const start = this.pageIndex * this.pageSize;
    return data.slice(start, start + this.pageSize);
  }
  get totalFiltered(): number { return this.dataSource.filteredData.length; }
  get totalPages(): number { return Math.ceil(this.totalFiltered / this.pageSize); }
  get pageNumbers(): number[] { return Array.from({ length: this.totalPages }, (_, i) => i); }
  get pageEndIndex(): number { return Math.min((this.pageIndex + 1) * this.pageSize, this.totalFiltered); }

  goToPage(idx: number): void { this.pageIndex = idx; }
  prevPage(): void { if (this.pageIndex > 0) this.pageIndex--; }
  nextPage(): void { if (this.pageIndex < this.totalPages - 1) this.pageIndex++; }

  // ── Filtru tip fișă ───────────────────────────────────────────────────────
  activeTypeFilter: string | null = null;

  readonly typeFilters = [
    { value: null,          label: 'Toate',         icon: 'layout-grid' },
    { value: 'consultatie', label: 'Consultații',    icon: 'stethoscope' },
    { value: 'analiza',     label: 'Analize',        icon: 'test-tube'   },
    { value: 'tratament',   label: 'Tratamente',     icon: 'pill'        },
    { value: 'reteta',      label: 'Rețete',         icon: 'clipboard-text' },
    { value: 'investigatie',label: 'Investigații',   icon: 'microscope'  },
  ];

  // ── Adaugă semn vital pentru pacient ──────────────────────────────────────
  showVitalForm = false;
  savingVital = false;
  vitalType = 'pulse';
  vitalValue: number | null = null;
  vitalNotes = '';
  vitalTypes = [
    { value: 'pulse',              label: 'Puls',               unit: 'bpm'  },
    { value: 'temperature',        label: 'Temperatură',         unit: '°C'   },
    { value: 'weight',             label: 'Greutate',            unit: 'kg'   },
    { value: 'oxygen_sat',         label: 'Saturație O₂',        unit: '%'    },
    { value: 'blood_pressure_sys', label: 'Tensiune Sistolică',  unit: 'mmHg' },
    { value: 'blood_pressure_dia', label: 'Tensiune Diastolică', unit: 'mmHg' },
  ];
  get selectedVitalUnit(): string {
    return this.vitalTypes.find(v => v.value === this.vitalType)?.unit ?? '';
  }

  form: FormGroup;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private notification: NotificationService,
    private fb: FormBuilder,
    private dialog: MatDialog,
  ) {
    this.form = this.fb.group({
      record_type: ['consultatie', Validators.required],
      notes_encrypted: ['', Validators.required],
      data_encrypted: [''],
      diagnosis: [''],
      treatment: [''],
      analysis_result: [''],
    });
  }

  ngOnInit(): void {
    this.apiService.get<Patient[]>('/doctors/my-patients').subscribe({
      next: (data) => { this.patients = data; },
      error: () => {}
    });
  }

  ngAfterViewChecked(): void {
    if (this.paginator && !this.paginatorConnected && this.dataSource.data.length > 0) {
      this.dataSource.paginator = this.paginator;
      this.paginatorConnected = true;
    }
  }

  selectPatient(patient: Patient): void {
    this.selectedPatient = patient;
    this.showForm = false;
    this.paginatorConnected = false;
    this.activeTypeFilter = null;
    this.pageIndex = 0;
    this.loadRecords(patient.id);
  }

  loadRecords(patientId: string): void {
    this.loading = true;
    this.paginatorConnected = false;
    this.dataSource.filterPredicate = (row: MedicalRecord, filter: string) =>
      filter === '' || row.record_type === filter;
    this.apiService.get<MedicalRecord[]>(`/medical-records/patient/${patientId}`).subscribe({
      next: (data) => {
        this.dataSource.data = data;
        this.applyTypeFilter();
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  setTypeFilter(value: string | null): void {
    this.activeTypeFilter = value;
    this.pageIndex = 0;
    this.paginatorConnected = false;
    this.applyTypeFilter();
  }

  private applyTypeFilter(): void {
    this.dataSource.filter = this.activeTypeFilter ?? '';
    this.pageIndex = 0;
    if (this.dataSource.paginator) {
      this.dataSource.paginator.firstPage();
    }
  }

  countByType(type: string): number {
    return this.dataSource.data.filter(r => r.record_type === type).length;
  }

  saveRecord(): void {
    if (!this.selectedPatient || this.form.invalid) return;
    this.saving = true;
    this.successMessage = '';
    this.errorMessage = '';

    const payload = { ...this.form.value, patient_id: this.selectedPatient.id };

    this.apiService.post<MedicalRecord>('/medical-records/', payload).subscribe({
      next: () => {
        this.saving = false;
        this.successMessage = 'Înregistrare adăugată cu succes!';
        this.showForm = false;
        this.form.reset({ record_type: 'consultatie' });
        this.loadRecords(this.selectedPatient!.id);
      },
      error: () => {
        this.saving = false;
        this.errorMessage = 'Eroare la salvare.';
      }
    });
  }

  deleteRecord(recordId: string): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: 'Șterge înregistrare',
        message: 'Ești sigur că vrei să ștergi această înregistrare medicală? Acțiunea este ireversibilă.',
        confirmText: 'Șterge',
        danger: true,
      }
    });
    ref.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;
      this.apiService.delete(`/medical-records/${recordId}`).subscribe({
        next: () => { this.loadRecords(this.selectedPatient!.id); },
        error: () => {}
      });
    });
  }

  viewRecord(record: MedicalRecord): void {
    this.dialog.open(RecordDetailDialogComponent, {
      maxWidth: '95vw',
      panelClass: 'record-detail-panel',
      data: record,
    });
  }

  // ── Adaugă vital pentru pacient ───────────────────────────────────────────

  saveVital(): void {
    if (!this.selectedPatient || !this.vitalValue || this.savingVital) return;
    this.savingVital = true;
    this.apiService.post(`/vitals/patient/${this.selectedPatient.id}`, {
      vital_type: this.vitalType,
      value: this.vitalValue,
      notes: this.vitalNotes || null,
    }).subscribe({
      next: () => {
        this.savingVital = false;
        this.showVitalForm = false;
        this.vitalValue = null;
        this.vitalNotes = '';
        this.notification.success('Semn vital înregistrat cu succes.');
      },
      error: () => {
        this.savingVital = false;
        this.notification.error('Eroare la salvarea semnului vital.');
      },
    });
  }

  // ── Predicție Risc AI ─────────────────────────────────────────────────────

  analyzeRisk(): void {
    if (!this.selectedPatient) return;
    this.loadingRisk = true;
    const patientUserId = this.selectedPatient.user_id || this.selectedPatient.id;
    this.apiService.get<any>(`/risk/patient/${patientUserId}`).subscribe({
      next: (data) => {
        this.loadingRisk = false;
        this.dialog.open(RiskDialogComponent, {
          width: '560px',
          data,
          panelClass: 'risk-dialog-panel',
        });
      },
      error: () => { this.loadingRisk = false; },
    });
  }

  // ── Feature 13: Raport medical AI ─────────────────────────────────────────

  generateAIReport(): void {
    if (!this.selectedPatient) return;
    this.generatingReport = true;
    const token = localStorage.getItem('access_token');
    fetch(`/api/patients/${this.selectedPatient.id}/ai-report`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error('Report failed');
        return res.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const win = window.open(url, '_blank');
        if (!win) {
          this.notification.error('Activează pop-up-urile pentru a deschide raportul.');
        }
        setTimeout(() => URL.revokeObjectURL(url), 120000);
      })
      .catch(() => this.notification.error('Eroare la generarea raportului AI.'))
      .finally(() => { this.generatingReport = false; });
  }
}
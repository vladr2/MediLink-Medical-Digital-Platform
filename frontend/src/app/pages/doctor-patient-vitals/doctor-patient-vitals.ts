import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { NgApexchartsModule } from 'ng-apexcharts';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { NotificationService } from '../../services/notification';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface Patient {
  id: string;
  user_id?: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

interface VitalSign {
  id: string;
  patient_id: string;
  vital_type: string;
  value: number;
  unit: string;
  recorded_at: string;
  notes: string | null;
}

@Component({
  selector: 'app-doctor-patient-vitals',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, NgApexchartsModule, SkeletonComponent],
  templateUrl: './doctor-patient-vitals.html',
})
export class DoctorPatientVitalsComponent implements OnInit {
  patients: Patient[] = [];
  selectedPatient: Patient | null = null;
  vitals: VitalSign[] = [];
  loading = false;
  loadingPats = false;

  selectedType = 'pulse';

  vitalTypes = [
    { key: 'pulse',               label: 'Puls',               unit: 'bpm',   color: '#ef4444', icon: 'heart-pulse'  },
    { key: 'blood_pressure_sys',  label: 'Tensiune sistolică',  unit: 'mmHg',  color: '#f97316', icon: 'activity'     },
    { key: 'blood_pressure_dia',  label: 'Tensiune diastolică', unit: 'mmHg',  color: '#eab308', icon: 'activity'     },
    { key: 'weight',              label: 'Greutate',            unit: 'kg',    color: '#22c55e', icon: 'weight'       },
    { key: 'temperature',         label: 'Temperatură',         unit: '°C',    color: '#3b82f6', icon: 'thermometer'  },
    { key: 'oxygen_sat',          label: 'Saturație O₂',        unit: '%',     color: '#8b5cf6', icon: 'lungs'        },
  ];

  // ── Add vital form ────────────────────────────────────────────────────────
  showForm   = false;
  savingVital = false;
  vitalType   = 'pulse';
  vitalValue: number | null = null;
  vitalNotes  = '';

  chart: any = {};

  get selectedTypeInfo() {
    return this.vitalTypes.find(t => t.key === this.selectedType) || this.vitalTypes[0];
  }

  get selectedVitalUnit(): string {
    return this.vitalTypes.find(v => v.key === this.vitalType)?.unit ?? '';
  }

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private notification: NotificationService,
  ) {}

  ngOnInit(): void {
    this.loadingPats = true;
    this.authService.currentUser$.subscribe(u => {
      const endpoint = u?.role === 'doctor' ? '/doctors/my-patients' : '/patients/';
      this.apiService.get<Patient[]>(endpoint).subscribe({
        next: (data) => { this.patients = data; this.loadingPats = false; },
        error: ()    => { this.loadingPats = false; },
      });
    });
  }

  patientName(p: Patient): string {
    const n = `${p.first_name || ''} ${p.last_name || ''}`.trim();
    return n || p.email;
  }

  onPatientChange(p: Patient | null): void {
    this.selectedPatient = p;
    this.showForm = false;
    this.vitals = [];
    this.chart  = {};
    if (p) this.loadVitals(p.id);
  }

  loadVitals(patientId: string): void {
    this.loading = true;
    this.apiService.get<VitalSign[]>(`/vitals/patient/${patientId}`).subscribe({
      next: (data) => {
        this.vitals = data ?? [];
        this.buildChart();
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  // ── Chart ─────────────────────────────────────────────────────────────────

  getChartData(type: string): { x: string; y: number }[] {
    return this.vitals
      .filter(v => v.vital_type === type)
      .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime())
      .map(v => ({
        x: new Date(v.recorded_at).toLocaleDateString('ro-RO', { day: '2-digit', month: 'short', year: '2-digit' }),
        y: v.value,
      }));
  }

  buildChart(): void {
    const typeInfo = this.selectedTypeInfo;
    const data = this.getChartData(this.selectedType);
    if (!data.length) { this.chart = {}; return; }

    this.chart = {
      series: [{ name: typeInfo.label, data: data.map(d => d.y) }],
      chart: { type: 'line', height: 280, toolbar: { show: false }, zoom: { enabled: false }, fontFamily: 'inherit' },
      stroke: { curve: 'smooth', width: 3, colors: [typeInfo.color] },
      markers: { size: 5, colors: [typeInfo.color], strokeColors: '#fff', strokeWidth: 2 },
      xaxis: {
        categories: data.map(d => d.x),
        labels: { style: { fontSize: '11px', colors: '#94a3b8' }, rotate: -30 },
        axisBorder: { show: false }, axisTicks: { show: false },
      },
      yaxis: {
        labels: { style: { fontSize: '11px', colors: '#94a3b8' }, formatter: (val: number) => `${val} ${typeInfo.unit}` },
      },
      grid: { borderColor: '#e2e8f0', strokeDashArray: 4, padding: { left: 10, right: 10 } },
      tooltip: { y: { formatter: (val: number) => `${val} ${typeInfo.unit}` } },
      colors: [typeInfo.color],
      fill: {
        type: 'gradient',
        gradient: { shade: 'light', type: 'vertical', shadeIntensity: 0.3, opacityFrom: 0.35, opacityTo: 0.05 },
      },
    };
  }

  selectType(key: string): void {
    this.selectedType = key;
    this.buildChart();
  }

  get recentVitals(): VitalSign[] {
    return this.vitals
      .filter(v => v.vital_type === this.selectedType)
      .sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime())
      .slice(0, 10);
  }

  // ── Save vital ────────────────────────────────────────────────────────────

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
        this.showForm    = false;
        this.vitalValue  = null;
        this.vitalNotes  = '';
        this.notification.success('Semn vital înregistrat cu succes.');
        this.loadVitals(this.selectedPatient!.id);
      },
      error: () => {
        this.savingVital = false;
        this.notification.error('Eroare la salvarea semnului vital.');
      },
    });
  }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('ro-RO', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { NgApexchartsModule } from 'ng-apexcharts';
import { ApiService } from '../../services/api';
import { AuthService, User } from '../../services/auth';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface VitalSign {
  id: string;
  patient_id: string;
  vital_type: string;
  value: number;
  unit: string;
  recorded_at: string;
  notes: string | null;
}

const VITAL_CONFIG: { type: string; label: string; unit: string; color: string; icon: string }[] = [
  { type: 'pulse',              label: 'Puls',              unit: 'bpm',   color: '#ef4444', icon: 'heart-pulse' },
  { type: 'weight',             label: 'Greutate',          unit: 'kg',    color: '#2563eb', icon: 'scale' },
  { type: 'temperature',        label: 'Temperatură',       unit: '°C',    color: '#f97316', icon: 'temperature' },
  { type: 'oxygen_sat',         label: 'Saturație O₂',      unit: '%',     color: '#0ea5e9', icon: 'lungs' },
  { type: 'blood_pressure_sys', label: 'Tensiune Sistolică', unit: 'mmHg', color: '#7c3aed', icon: 'activity' },
  { type: 'blood_pressure_dia', label: 'Tensiune Diastolică',unit: 'mmHg', color: '#db2777', icon: 'activity' },
];

@Component({
  selector: 'app-my-stats',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, NgApexchartsModule, SkeletonComponent],
  templateUrl: './my-stats.html',
})
export class MyStatsComponent implements OnInit {
  loading = true;
  vitals: VitalSign[] = [];
  currentUser: User | null = null;

  vitalConfig = VITAL_CONFIG;
  selectedTypes = new Set<string>(['pulse', 'weight', 'temperature', 'oxygen_sat', 'blood_pressure_sys', 'blood_pressure_dia']);
  vitalCharts: Record<string, any> = {};

  constructor(private apiService: ApiService, private authService: AuthService) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(u => { this.currentUser = u; });
    this.loadData();
  }

  // ── Getters ───────────────────────────────────────────────────────────────

  get totalVitals(): number { return this.vitals.length; }

  get lastMeasurement(): string {
    if (!this.vitals.length) return '—';
    const sorted = [...this.vitals].sort(
      (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime()
    );
    return new Date(sorted[0].recorded_at).toLocaleDateString('ro-RO', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  getVitalsOfType(type: string): VitalSign[] {
    return this.vitals
      .filter(v => v.vital_type === type)
      .sort((a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime());
  }

  isSelected(type: string): boolean { return this.selectedTypes.has(type); }

  hasData(type: string): boolean { return this.getVitalsOfType(type).length > 0; }

  toggleType(type: string): void {
    if (this.selectedTypes.has(type)) {
      this.selectedTypes.delete(type);
    } else {
      this.selectedTypes.add(type);
    }
  }

  // ── Data loading ──────────────────────────────────────────────────────────

  loadData(): void {
    this.loading = true;
    this.apiService.get<VitalSign[]>('/vitals/my').subscribe({
      next: (vitals) => {
        this.vitals = vitals ?? [];
        this.buildCharts();
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  // ── Chart builders ────────────────────────────────────────────────────────

  buildCharts(): void {
    for (const cfg of VITAL_CONFIG) {
      const data = this.getVitalsOfType(cfg.type).map(v => ({
        x: new Date(v.recorded_at).getTime(),
        y: v.value,
      }));
      this.vitalCharts[cfg.type] = {
        series: [{ name: cfg.label, data }],
        chart: { type: 'line', height: 200, background: 'transparent', toolbar: { show: false }, fontFamily: 'inherit' },
        stroke: { curve: 'smooth', width: 2 },
        markers: { size: 4 },
        xaxis: { type: 'datetime', labels: { format: 'dd MMM' } },
        yaxis: { labels: { formatter: (v: number) => v + ' ' + cfg.unit } },
        colors: [cfg.color],
        grid: { borderColor: '#f1f5f9' },
        tooltip: { x: { format: 'dd MMM yyyy' } },
      };
    }
  }

  getConfigForType(type: string) {
    return VITAL_CONFIG.find(c => c.type === type)!;
  }

  get activeConfigs() {
    return VITAL_CONFIG.filter(c => this.selectedTypes.has(c.type));
  }
}

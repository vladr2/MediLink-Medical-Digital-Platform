import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { NgApexchartsModule, ApexChart, ApexNonAxisChartSeries,
         ApexAxisChartSeries, ApexXAxis, ApexPlotOptions,
         ApexDataLabels, ApexTooltip } from 'ng-apexcharts';
import { ApiService } from '../../services/api';
import { AuthService, User } from '../../services/auth';
import { ThemeService } from '../../services/theme';
import { Subject, takeUntil } from 'rxjs';

interface DoctorProfile {
  id: string;
  specialization: string;
  department: string;
  bio: string;
  license_number: string;
  schedule: string;
}

interface Appointment {
  id: string;
  patient_id: string;
  datetime: string;
  status: string;
  notes: string;
  reason: string;
}

interface Patient {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

@Component({
  selector: 'app-doctor-dashboard',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, NgApexchartsModule],
  templateUrl: './doctor-dashboard.html',
})
export class DoctorDashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  doctorProfile: DoctorProfile | null = null;
  appointments: Appointment[] = [];
  patients: Patient[] = [];
  loading = true;
  displayedColumns = ['datetime', 'patient', 'status', 'actions'];

  // Grafic donut — distribuție status programări
  statusDonutChart: any;
  // Grafic bar — programări pe zi din săptămâna curentă
  weekBarChart: any;
  private destroy$ = new Subject<void>();

  // ── Dashboard Widget Settings ──────────────────────────────────────────────
  showWidgetSettings = false;
  widgets = {
    stats:         true,
    donut_chart:   true,
    bar_chart:     true,
    appointments:  true,
  };

  widgetDefs = [
    { key: 'stats',        label: 'Statistici',             icon: 'chart-bar' },
    { key: 'donut_chart',  label: 'Grafic distribuție',     icon: 'chart-donut' },
    { key: 'bar_chart',    label: 'Grafic 7 zile',          icon: 'chart-histogram' },
    { key: 'appointments', label: 'Programări viitoare',    icon: 'calendar' },
  ];

  private readonly WIDGET_KEY = 'medilink_doctor_widgets';

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    public themeService: ThemeService,
  ) {}

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadWidgets(): void {
    try {
      const saved = localStorage.getItem(this.WIDGET_KEY);
      if (saved) this.widgets = { ...this.widgets, ...JSON.parse(saved) };
    } catch {}
  }

  isWidgetVisible(key: string): boolean {
    return (this.widgets as Record<string, boolean>)[key];
  }

  toggleWidget(key: string): void {
    (this.widgets as Record<string, boolean>)[key] = !this.isWidgetVisible(key);
    localStorage.setItem(this.WIDGET_KEY, JSON.stringify(this.widgets));
  }

  ngOnInit(): void {
    this.loadWidgets();
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });

    // Rebuild charts when theme changes
    this.themeService.isDark$.pipe(takeUntil(this.destroy$)).subscribe(() => {
      if (this.appointments.length > 0) this.buildCharts();
    });

    this.apiService.get<DoctorProfile>('/doctors/me').subscribe({
      next: (p) => { this.doctorProfile = p; this.loading = false; },
      error: () => { this.loading = false; }
    });

    this.apiService.get<Appointment[]>('/appointments/').subscribe({
      next: (data) => {
        this.appointments = data.sort((a, b) =>
          new Date(b.datetime).getTime() - new Date(a.datetime).getTime()
        );
        this.buildCharts();
      },
      error: () => {}
    });

    this.apiService.get<Patient[]>('/doctors/my-patients').subscribe({
      next: (data) => { this.patients = data; },
      error: () => {}
    });
  }

  buildCharts(): void {
    const pending   = this.appointments.filter(a => a.status === 'pending').length;
    const confirmed = this.appointments.filter(a => a.status === 'confirmed').length;
    const completed = this.appointments.filter(a => a.status === 'completed').length;
    const cancelled = this.appointments.filter(a => a.status === 'cancelled').length;

    const fg = this.themeService.isDark ? '#94a3b8' : '#111c2d';
    const gridColor = this.themeService.isDark ? '#2d3f5c' : '#f0f0f0';

    this.statusDonutChart = {
      series: [pending, confirmed, completed, cancelled],
      chart: { type: 'donut', height: 280, fontFamily: 'inherit',
               background: 'transparent', foreColor: fg },
      theme: { mode: this.themeService.isDark ? 'dark' : 'light' },
      labels: ['În așteptare', 'Confirmate', 'Finalizate', 'Anulate'],
      colors: ['#fb8c00', '#1976d2', '#2e7d32', '#c62828'],
      legend: { position: 'bottom' },
      dataLabels: {
        enabled: true,
        formatter: (val: number) => `${Math.round(val)}%`,
        style: { fontSize: '13px', fontWeight: '700' },
        dropShadow: { enabled: false },
      },
      plotOptions: { pie: { donut: { size: '60%' } } },
      tooltip: { y: { formatter: (v: number) => `${v} programări` } }
    };

    // Programări pe ziua săptămânii (ultimele 7 zile)
    const days = ['Lun', 'Mar', 'Mie', 'Joi', 'Vin', 'Sâm', 'Dum'];
    const counts = new Array(7).fill(0);
    const now = new Date();
    this.appointments.forEach(a => {
      const d = new Date(a.datetime);
      const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
      if (diff >= 0 && diff < 7) {
        const idx = (d.getDay() + 6) % 7; // 0=Lun
        counts[idx]++;
      }
    });

    this.weekBarChart = {
      series: [{ name: 'Programări', data: counts }],
      chart: { type: 'bar', height: 280, fontFamily: 'inherit', toolbar: { show: false },
               background: 'transparent', foreColor: fg },
      theme: { mode: this.themeService.isDark ? 'dark' : 'light' },
      colors: ['#1976d2'],
      xaxis: { categories: days },
      plotOptions: { bar: { borderRadius: 6, columnWidth: '50%' } },
      dataLabels: { enabled: false },
      grid: { borderColor: gridColor },
      tooltip: { y: { formatter: (v: number) => `${v} programări` } }
    };
  }

  // ── Statistici ─────────────────────────────────────────────────────────────
  get todayAppointments(): Appointment[] {
    const today = new Date().toDateString();
    return this.appointments.filter(a =>
      new Date(a.datetime).toDateString() === today &&
      a.status !== 'cancelled'
    );
  }

  get todayCount(): number {
    return this.todayAppointments.length;
  }

  get upcomingCount(): number {
    const now = new Date();
    return this.appointments.filter(
      a => new Date(a.datetime) > now && a.status !== 'cancelled'
    ).length;
  }

  get upcomingAppointments(): Appointment[] {
    const now = new Date();
    return this.appointments
      .filter(a => new Date(a.datetime) > now && a.status !== 'cancelled')
      .sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime())
      .slice(0, 8);
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  getStatusColor(status: string): string {
    const map: any = { pending: 'warn', confirmed: 'primary', completed: 'accent', cancelled: '' };
    return map[status] || '';
  }

  getStatusLabel(status: string): string {
    const map: any = { pending: 'În așteptare', confirmed: 'Confirmat', completed: 'Finalizat', cancelled: 'Anulat' };
    return map[status] || status;
  }

  getPatientName(patientId: string): string {
    const p = this.patients.find(x => x.id === patientId);
    if (!p) return '-';
    return (p.first_name || p.last_name) ? `${p.first_name || ''} ${p.last_name || ''}`.trim() : p.email;
  }

  updateStatus(appointmentId: string, status: string): void {
    this.apiService.patch<any>(`/appointments/${appointmentId}`, { status }).subscribe({
      next: (updated) => {
        const idx = this.appointments.findIndex(a => a.id === appointmentId);
        if (idx !== -1) this.appointments[idx] = updated;
        this.buildCharts();
      },
      error: () => {}
    });
  }
}

import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MaterialModule } from '../../material.module';
import { AuthService, User } from '../../services/auth';
import { ApiService } from '../../services/api';
import { TablerIconsModule } from 'angular-tabler-icons';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { ThemeService } from '../../services/theme';
import { Subject, takeUntil } from 'rxjs';
import {
  NgApexchartsModule,
  ApexChart,
  ApexNonAxisChartSeries,
  ApexLegend,
  ApexResponsive,
  ApexDataLabels,
  ApexTooltip,
} from 'ng-apexcharts';

export type DonutChartOptions = {
  series: ApexNonAxisChartSeries;
  chart: ApexChart;
  labels: string[];
  legend: ApexLegend;
  responsive: ApexResponsive[];
  colors: string[];
  dataLabels: ApexDataLabels;
  tooltip: ApexTooltip;
};

@Component({
  selector: 'app-medical-dashboard',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, SkeletonComponent, NgApexchartsModule],
  templateUrl: './medical-dashboard.html',
})
export class MedicalDashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  nextAppointment: any = null;
  recentRecords: any[] = [];
  allAppointments: any[] = [];
  patientId: string | null = null;
  loadingData = false;

  appointmentDonutChart: any = {};
  private destroy$ = new Subject<void>();

  // ── Dashboard Widget Settings ──────────────────────────────────────────────
  showWidgetSettings = false;
  widgets = {
    stats:            true,
    next_appointment: true,
    recent_records:   true,
    chart:            true,
    health_tips:      true,
  };

  widgetDefs = [
    { key: 'stats',            label: 'Statistici programări',   icon: 'chart-bar' },
    { key: 'next_appointment', label: 'Programarea următoare',   icon: 'calendar-event' },
    { key: 'recent_records',   label: 'Înregistrări recente',    icon: 'notes-medical' },
    { key: 'chart',            label: 'Grafic distribuție',      icon: 'chart-donut' },
    { key: 'health_tips',      label: 'Sfaturi sănătate',        icon: 'heart' },
  ];

  private readonly WIDGET_KEY = 'medilink_patient_widgets';

  get totalAppointments(): number { return this.allAppointments.length; }
  get pendingAppointments(): number { return this.allAppointments.filter(a => a.status === 'pending').length; }
  get upcomingAppointments(): number {
    const now = new Date();
    return this.allAppointments.filter(a => new Date(a.datetime) > now && a.status !== 'cancelled').length;
  }

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private router: Router,
    public themeService: ThemeService,
  ) {}

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadWidgets(): void {
    try {
      const saved = localStorage.getItem(this.WIDGET_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Ignoră quick_nav din localStorage (widget eliminat)
        delete parsed['quick_nav'];
        this.widgets = { ...this.widgets, ...parsed };
      }
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
    // Rebuild chart when theme changes
    this.themeService.isDark$.pipe(takeUntil(this.destroy$)).subscribe(() => {
      if (this.allAppointments.length > 0) this.buildPatientChart();
    });

    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user?.role === 'doctor') {
        this.router.navigate(['/dashboard/doctor-dashboard']);
      } else if (user?.role === 'assistant') {
        this.router.navigate(['/dashboard/assistant-dashboard']);
      } else if (user?.role === 'admin') {
        this.router.navigate(['/dashboard/admin-dashboard']);
      } else if (user?.role === 'patient') {
        // Feature 15: redirect to onboarding wizard for new patients
        const onboardingDone = localStorage.getItem(`medilink_onboarding_${user.id}`);
        if (!user.first_name && !user.last_name && !onboardingDone) {
          this.router.navigate(['/dashboard/onboarding']);
          return;
        }
        this.loadPatientData();
      }
    });
  }

  loadPatientData(): void {
    this.loadingData = true;
    this.apiService.get<any>('/patients/me').subscribe({
      next: (patient) => {
        this.patientId = patient.id;
        this.loadNextAppointment();
        this.loadRecentRecords(patient.id);
      },
      error: () => { this.loadingData = false; }
    });
  }

  loadNextAppointment(): void {
    this.apiService.get<any[]>('/appointments/').subscribe({
      next: (appointments) => {
        this.allAppointments = appointments;
        const now = new Date();
        // Cauta urmatoarea programare viitoare
        const upcoming = appointments
          .filter(a => new Date(a.datetime) > now && a.status !== 'cancelled')
          .sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime());

        if (upcoming.length > 0) {
          this.nextAppointment = upcoming[0];
        } else {
          // Daca nu sunt programari viitoare, arata cea mai recenta
          const past = appointments
            .filter(a => a.status !== 'cancelled')
            .sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime());
          this.nextAppointment = past[0] || null;
        }
        this.buildPatientChart();
      },
      error: () => {}
    });
  }

  buildPatientChart(): void {
    const statuses = ['pending', 'confirmed', 'completed', 'cancelled'];
    const labels = ['În așteptare', 'Confirmate', 'Finalizate', 'Anulate'];
    const colors = ['#ff9800', '#1976d2', '#4caf50', '#f44336'];

    const series = statuses.map(s => this.allAppointments.filter(a => a.status === s).length);

    // Daca toate sunt 0, nu afisa graficul
    if (series.every(v => v === 0)) {
      this.appointmentDonutChart = {};
      return;
    }

    this.appointmentDonutChart = {
      series,
      chart: { type: 'donut', height: 260, fontFamily: 'Roboto, sans-serif', toolbar: { show: false },
               background: 'transparent', foreColor: this.themeService.isDark ? '#94a3b8' : '#111c2d' },
      theme: { mode: this.themeService.isDark ? 'dark' : 'light' },
      labels,
      colors,
      legend: { position: 'bottom', fontSize: '13px' },
      dataLabels: { enabled: true, formatter: (val: number) => Math.round(val) + '%' },
      tooltip: { y: { formatter: (val: number) => val + ' programări' } },
      responsive: [{ breakpoint: 480, options: { chart: { height: 220 }, legend: { position: 'bottom' } } }],
    };
  }

  loadRecentRecords(patientId: string): void {
    this.apiService.get<any[]>(`/medical-records/patient/${patientId}`).subscribe({
      next: (records) => {
        this.recentRecords = records.slice(0, 3);
        this.loadingData = false;
      },
      error: () => { this.loadingData = false; }
    });
  }

  getAppointmentStatusColor(status: string): string {
    const map: any = { pending: 'warn', confirmed: 'primary', completed: 'accent', cancelled: '' };
    return map[status] || '';
  }

  getRecordTypeIcon(type: string): string {
    const map: any = {
      analysis: 'test-pipe',
      treatment: 'pill',
      consultation: 'stethoscope',
      prescription: 'prescription',
    };
    return map[type] || 'file-description';
  }

  navigate(route: string): void {
    this.router.navigate([route]);
  }
}

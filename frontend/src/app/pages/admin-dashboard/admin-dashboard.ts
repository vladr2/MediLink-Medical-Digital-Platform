import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { AuthService, User } from '../../services/auth';
import { Router } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatTableDataSource } from '@angular/material/table';
import { CreateUserDialogComponent } from './create-user-dialog.component';
import { AuditLogDialogComponent } from './audit-log-dialog.component';
import { ConfirmDialogComponent } from '../../components/confirm-dialog/confirm-dialog.component';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import {
  NgApexchartsModule,
  ApexChart,
  ApexNonAxisChartSeries,
  ApexLegend,
  ApexResponsive,
  ApexAxisChartSeries,
  ApexXAxis,
  ApexPlotOptions,
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
};

export type BarChartOptions = {
  series: ApexAxisChartSeries;
  chart: ApexChart;
  xaxis: ApexXAxis;
  plotOptions: ApexPlotOptions;
  dataLabels: ApexDataLabels;
  tooltip: ApexTooltip;
  colors: string[];
  yaxis?: any;
};

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, ReactiveFormsModule, FormsModule, MatDialogModule, MatSortModule, MatPaginatorModule, NgApexchartsModule, SkeletonComponent],
  templateUrl: './admin-dashboard.html',
})
export class AdminDashboardComponent implements OnInit, AfterViewInit {
  currentUser: User | null = null;
  users: any[] = [];
  usersDataSource = new MatTableDataSource<any>([]);
  appointments: any[] = [];
  filteredAppointments: any[] = [];
  loading = true;
  usersLoaded = false;
  appointmentsLoaded = false;
  doctorsLoaded = false;
  displayedColumns = ['email', 'full_name', 'role', 'is_active', 'created_at', 'actions'];
  appointmentColumns = ['datetime', 'doctor', 'status', 'reason', 'actions'];
  auditLogs: any[] = [];
  loadingAudit = true;
  auditColumns = ['created_at', 'user_email', 'action', 'details', 'ip_address'];
  searchQuery = '';
  selectedRole = 'all';
  selectedDoctorFilter = 'all';
  doctors: any[] = [];
  dateFrom = '';
  dateTo = '';
  dateFromMoment: any = null;
  dateToMoment: any = null;

  @ViewChild(MatSort) sort!: MatSort;
  @ViewChild(MatPaginator) paginator!: MatPaginator;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router,
    private dialog: MatDialog,
    private fb: FormBuilder,
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });
    this.loadUsers();
    this.apiService.get<any[]>('/appointments/').subscribe({
      next: (data) => {
        this.appointments = data;
        this.filteredAppointments = data;
        this.appointmentsLoaded = true;
        this.tryBuildCharts();
      },
      error: () => {}
    });
    this.apiService.get<any[]>('/doctors/').subscribe({
      next: (data) => {
        this.doctors = data;
        this.doctorsLoaded = true;
        this.tryBuildCharts();
      },
      error: () => { this.doctorsLoaded = true; this.tryBuildCharts(); }
    });
    this.apiService.get<any[]>('/audit/').subscribe({
      next: (data) => {
        this.auditLogs = data;
        this.loadingAudit = false;
      },
      error: () => { this.loadingAudit = false; }
    });
  }

  ngAfterViewInit(): void {
    this.usersDataSource.sortingDataAccessor = (item, property) => {
      switch(property) {
        case 'full_name': return `${item.first_name || ''} ${item.last_name || ''}`.trim().toLowerCase();
        case 'created_at': return new Date(item.created_at).getTime();
        case 'is_active': return item.is_active ? 1 : 0;
        default: return item[property] ? item[property].toString().toLowerCase() : '';
      }
    };
    this.usersDataSource.sort = this.sort;
    this.usersDataSource.paginator = this.paginator;
  }

  loadUsers(): void {
    this.apiService.get<any[]>('/users/').subscribe({
      next: (data) => {
        this.users = data;
        this.usersDataSource.data = data;
        this.loading = false;
        this.usersLoaded = true;
        this.tryBuildCharts();
      },
      error: () => { this.loading = false; }
    });
  }

  tryBuildCharts(): void {
    if (this.usersLoaded && this.appointmentsLoaded && this.doctorsLoaded) {
      this.buildCharts();
    }
  }

  filterUsers(event: any): void {
    this.searchQuery = event.target.value.toLowerCase();
    this.applyFilters();
  }

  filterByRole(role: string): void {
    this.selectedRole = role;
    this.applyFilters();
  }

  filterByDate(type: string, event: any): void {
    if (type === 'from') this.dateFrom = event.target.value;
    if (type === 'to') this.dateTo = event.target.value;
    this.applyFilters();
  }

  onFilterDateFrom(e: any): void {
    this.dateFrom = e.value ? e.value.format('YYYY-MM-DD') : '';
    this.applyFilters();
  }

  onFilterDateTo(e: any): void {
    this.dateTo = e.value ? e.value.format('YYYY-MM-DD') : '';
    this.applyFilters();
  }

  applyFilters(): void {
    this.usersDataSource.data = this.users.filter(u => {
      const matchesSearch = !this.searchQuery ||
        u.email.toLowerCase().includes(this.searchQuery) ||
        ((u.first_name && u.first_name.toLowerCase().includes(this.searchQuery)) ||
        (u.last_name && u.last_name.toLowerCase().includes(this.searchQuery)));
      const matchesRole = this.selectedRole === 'all' || u.role === this.selectedRole;
      const createdAt = new Date(u.created_at);
      const matchesFrom = !this.dateFrom || createdAt >= new Date(this.dateFrom);
      const matchesTo = !this.dateTo || createdAt <= new Date(this.dateTo);
      return matchesSearch && matchesRole && matchesFrom && matchesTo;
    });
  }

  filterAppointmentsByDoctor(doctorId: string): void {
    this.selectedDoctorFilter = doctorId;
    if (doctorId === 'all') {
      this.filteredAppointments = this.appointments;
    } else {
      this.filteredAppointments = this.appointments.filter(a => a.doctor_id === doctorId);
    }
  }

  getDoctorName(doctorId: string): string {
    const doctor = this.doctors.find(d => d.user_id === doctorId);
    if (!doctor) return '-';
    return (doctor.first_name || doctor.last_name) ? `${doctor.first_name} ${doctor.last_name}` : doctor.email;
  }

  updateAppointmentStatus(appointmentId: string, status: string): void {
    this.apiService.patch<any>(`/appointments/${appointmentId}`, { status }).subscribe({
      next: (updated) => {
        const index = this.appointments.findIndex(a => a.id === appointmentId);
        if (index !== -1) {
          this.appointments[index] = updated;
          this.filterAppointmentsByDoctor(this.selectedDoctorFilter);
        }
      },
      error: () => {}
    });
  }

  openCreateDialog(): void {
    const dialogRef = this.dialog.open(CreateUserDialogComponent, {
      width: '550px',
      minWidth: '450px',
    });
    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.apiService.post<any>('/users/', result).subscribe({
          next: () => { this.loadUsers(); },
          error: () => {}
        });
      }
    });
  }

  openAuditDialog(): void {
    this.dialog.open(AuditLogDialogComponent, {
      width: '90vw',
      maxWidth: '1200px',
      data: this.auditLogs,
    });
  }

  get totalUsers(): number { return this.users.length; }
  get activeUsers(): number { return this.users.filter(u => u.is_active).length; }
  get doctorCount(): number { return this.users.filter(u => u.role === 'doctor').length; }
  get patientCount(): number { return this.users.filter(u => u.role === 'patient').length; }
  get assistantCount(): number { return this.users.filter(u => u.role === 'assistant').length; }
  get totalAppointments(): number { return this.appointments.length; }
  get pendingAppointments(): number { return this.appointments.filter(a => a.status === 'pending').length; }
  get confirmedAppointments(): number { return this.appointments.filter(a => a.status === 'confirmed').length; }
  get completedAppointments(): number { return this.appointments.filter(a => a.status === 'completed').length; }
  get cancelledAppointments(): number { return this.appointments.filter(a => a.status === 'cancelled').length; }
  get recentAuditLogs(): any[] { return this.auditLogs.slice(0, 10); }

  // ── Feature 4: Statistici avansate ─────────────────────────
  get appointmentsThisMonth(): number {
    const now = new Date();
    return this.appointments.filter(a => {
      const d = new Date(a.datetime);
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length;
  }

  get cancellationRate(): number {
    if (this.appointments.length === 0) return 0;
    return Math.round(this.cancelledAppointments / this.appointments.length * 100);
  }

  get avgAppointmentsPerDoctor(): number {
    if (this.doctorCount === 0) return 0;
    return Math.round(this.totalAppointments / this.doctorCount);
  }

  getAppointmentsByMonth(): { labels: string[], data: number[] } {
    const months: string[] = [];
    const counts: number[] = [];
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const label = d.toLocaleDateString('ro-RO', { month: 'short', year: '2-digit' });
      months.push(label);
      const count = this.appointments.filter(a => {
        const ad = new Date(a.datetime);
        return ad.getMonth() === d.getMonth() && ad.getFullYear() === d.getFullYear();
      }).length;
      counts.push(count);
    }
    return { labels: months, data: counts };
  }

  getTopDoctors(): { names: string[], counts: number[] } {
    const map = new Map<string, number>();
    this.appointments.forEach(a => {
      map.set(a.doctor_id, (map.get(a.doctor_id) || 0) + 1);
    });
    const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
    const names = sorted.map(([id]) => {
      const doc = this.doctors.find((d: any) => d.user_id === id);
      if (!doc) return 'Necunoscut';
      return (doc.first_name || doc.last_name) ? `${doc.first_name || ''} ${doc.last_name || ''}`.trim() : doc.email;
    });
    const counts = sorted.map(([, c]) => c);
    return { names, counts };
  }

  // ── Grafice ApexCharts ──────────────────────────────────────

  appointmentDonutChart: any = {};
  userRolesBarChart: any = {};
  appointmentsByMonthChart: any = {};
  topDoctorsChart: any = {};

  buildCharts(): void {
    this.appointmentDonutChart = {
      series: [
        this.pendingAppointments,
        this.confirmedAppointments,
        this.completedAppointments,
        this.cancelledAppointments,
      ],
      chart: { type: 'donut', height: 300, fontFamily: 'Roboto, sans-serif', background: 'transparent' },
      labels: ['În așteptare', 'Confirmate', 'Finalizate', 'Anulate'],
      colors: ['#fb8c00', '#1976d2', '#388e3c', '#d32f2f'],
      legend: { position: 'bottom', fontSize: '13px' },
      responsive: [{ breakpoint: 480, options: { chart: { height: 220 } } }],
    };

    this.userRolesBarChart = {
      series: [{ name: 'Utilizatori', data: [this.doctorCount, this.patientCount, this.assistantCount] }],
      chart: { type: 'bar', height: 300, toolbar: { show: false }, fontFamily: 'Roboto, sans-serif', background: 'transparent' },
      xaxis: { categories: ['Doctori', 'Pacienți', 'Asistenți'] },
      plotOptions: { bar: { borderRadius: 6, columnWidth: '45%', distributed: true } },
      dataLabels: { enabled: true },
      tooltip: { y: { formatter: (val: number) => `${val} utilizatori` } },
      colors: ['#1976d2', '#388e3c', '#7b1fa2'],
    };

    // Programări pe lună — ultimele 6 luni
    const monthly = this.getAppointmentsByMonth();
    this.appointmentsByMonthChart = {
      series: [{ name: 'Programări', data: monthly.data }],
      chart: { type: 'bar', height: 300, toolbar: { show: false }, fontFamily: 'Roboto, sans-serif', background: 'transparent' },
      xaxis: { categories: monthly.labels },
      plotOptions: { bar: { borderRadius: 5, columnWidth: '55%' } },
      dataLabels: { enabled: true, style: { fontSize: '12px' } },
      colors: ['#2563eb'],
      tooltip: { y: { formatter: (val: number) => `${val} programări` } },
      yaxis: { min: 0, forceNiceScale: true, labels: { formatter: (v: number) => Math.round(v).toString() } },
    };

    // Top 5 doctori activi — bar orizontal
    const top = this.getTopDoctors();
    if (top.names.length > 0) {
      this.topDoctorsChart = {
        series: [{ name: 'Programări', data: top.counts }],
        chart: { type: 'bar', height: 300, toolbar: { show: false }, fontFamily: 'Roboto, sans-serif', background: 'transparent' },
        plotOptions: { bar: { horizontal: true, borderRadius: 5, barHeight: '55%', distributed: true } },
        xaxis: { categories: top.names },
        dataLabels: { enabled: true, style: { fontSize: '12px' } },
        colors: ['#0d9488', '#2563eb', '#7c3aed', '#ea580c', '#db2777'],
        tooltip: { y: { formatter: (val: number) => `${val} programări` } },
        yaxis: { labels: { style: { fontSize: '12px' } } },
      };
    }
  }

  navigate(route: string): void {
    this.router.navigate([route]);
  }

  toggleActive(user: any): void {
    const action = user.is_active ? 'dezactivezi' : 'activezi';
    const ref = this.dialog.open(ConfirmDialogComponent, {
      width: '400px',
      data: {
        title: user.is_active ? 'Dezactivează cont' : 'Activează cont',
        message: `Ești sigur că vrei să ${action} contul pentru ${user.email}?`,
        confirmText: user.is_active ? 'Dezactivează' : 'Activează',
        danger: user.is_active,
      }
    });
    ref.afterClosed().subscribe(confirmed => {
      if (!confirmed) return;
      this.apiService.patch<any>(`/users/${user.id}/toggle-active`, {}).subscribe({
        next: (updated) => {
          const index = this.users.findIndex(u => u.id === user.id);
          if (index !== -1) {
            this.users[index] = updated;
            this.applyFilters();
          }
        },
        error: () => {}
      });
    });
  }

  getRoleColor(role: string): string {
    const colors: any = {
      admin: 'warn',
      doctor: 'primary',
      assistant: 'accent',
      patient: ''
    };
    return colors[role] || '';
  }

  getStatusColor(status: string): string {
    const colors: any = {
      pending: 'warn',
      confirmed: 'primary',
      completed: 'accent',
      cancelled: ''
    };
    return colors[status] || '';
  }

  exportAuditLog(): void {
    const token = localStorage.getItem('access_token');
    fetch('/api/audit/export', {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(response => response.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }
}
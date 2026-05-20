import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { AuthService, User } from '../../services/auth';
import { NotificationService } from '../../services/notification';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface Appointment {
  id: string;
  patient_id: string;
  doctor_id: string;
  datetime: string;
  status: string;
  reason: string;
  notes: string;
  patient_name?: string;
  doctor_name?: string;
}

interface Patient {
  id: string;
  user_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
}

@Component({
  selector: 'app-assistant-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './assistant-dashboard.html',
})
export class AssistantDashboardComponent implements OnInit {
  currentUser: User | null = null;
  appointments: Appointment[] = [];
  unassignedPatients: Patient[] = [];

  loading = true;
  updating: Record<string, boolean> = {};

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private notification: NotificationService,
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(u => { this.currentUser = u; });
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.apiService.get<Appointment[]>('/appointments/').subscribe({
      next: (data) => {
        this.appointments = data.sort(
          (a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime()
        );
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
    this.apiService.get<Patient[]>('/patients/unassigned').subscribe({
      next: (data) => { this.unassignedPatients = data; },
      error: () => {},
    });
  }

  // ── Stats ─────────────────────────────────────────────────────────────────

  get pendingAll(): Appointment[] {
    return this.appointments.filter(a => a.status === 'pending');
  }

  get todayAppointments(): Appointment[] {
    const today = new Date().toDateString();
    return this.appointments.filter(a =>
      new Date(a.datetime).toDateString() === today &&
      a.status !== 'cancelled'
    );
  }

  get confirmedToday(): Appointment[] {
    return this.todayAppointments.filter(a => a.status === 'confirmed');
  }

  get pendingToday(): Appointment[] {
    return this.todayAppointments.filter(a => a.status === 'pending');
  }

  get weekAppointments(): Appointment[] {
    const now = new Date();
    const day = now.getDay();
    const monday = new Date(now);
    monday.setDate(now.getDate() - (day === 0 ? 6 : day - 1));
    monday.setHours(0, 0, 0, 0);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return this.appointments.filter(a => {
      const dt = new Date(a.datetime);
      return dt >= monday && dt <= sunday && a.status !== 'cancelled';
    }).sort((a, b) => new Date(a.datetime).getTime() - new Date(b.datetime).getTime());
  }

  patientName(a: Appointment): string { return a.patient_name || '—'; }
  doctorName(a: Appointment): string  { return a.doctor_name  || '—'; }

  formatTime(dt: string): string {
    return new Date(dt).toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' });
  }
  formatDate(dt: string): string {
    return new Date(dt).toLocaleDateString('ro-RO', { day: '2-digit', month: 'short' });
  }

  statusColor(s: string): string {
    return s === 'pending' ? '#f59e0b' : s === 'confirmed' ? '#22c55e' :
           s === 'completed' ? '#2563eb' : '#94a3b8';
  }
  statusLabel(s: string): string {
    return s === 'pending' ? 'În așteptare' : s === 'confirmed' ? 'Confirmată' :
           s === 'completed' ? 'Finalizată' : 'Anulată';
  }

  // ── Acțiuni rapide ────────────────────────────────────────────────────────

  confirm(app: Appointment): void { this.updateStatus(app, 'confirmed'); }
  cancel(app: Appointment): void  { this.updateStatus(app, 'cancelled'); }

  private updateStatus(app: Appointment, status: string): void {
    this.updating[app.id] = true;
    this.apiService.patch(`/appointments/${app.id}`, { status }).subscribe({
      next: () => {
        app.status = status;
        this.updating[app.id] = false;
        this.notification.success(
          status === 'confirmed' ? 'Programare confirmată.' : 'Programare anulată.'
        );
      },
      error: () => {
        this.updating[app.id] = false;
        this.notification.error('Eroare la actualizarea programării.');
      },
    });
  }
}

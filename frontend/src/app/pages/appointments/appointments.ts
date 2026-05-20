import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { AuthService } from '../../services/auth';
import { MatNativeDateModule } from '@angular/material/core';
import { MAT_DATE_FORMATS, MAT_DATE_LOCALE } from '@angular/material/core';
import { MomentDateAdapter, MAT_MOMENT_DATE_ADAPTER_OPTIONS } from '@angular/material-moment-adapter';
import { DateAdapter } from '@angular/material/core';
import { MatDatepickerModule } from '@angular/material/datepicker';
import moment from 'moment';

export const MY_DATE_FORMATS = {
  parse: { dateInput: 'DD/MM/YYYY' },
  display: {
    dateInput: 'DD/MM/YYYY',
    monthYearLabel: 'MMM YYYY',
    dateA11yLabel: 'DD/MM/YYYY',
    monthYearA11yLabel: 'MMMM YYYY',
  }
};

interface Appointment {
  id: string;
  patient_id: string;
  doctor_id: string;
  datetime: string;
  status: string;
  notes: string;
  reason: string;
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
  selector: 'app-appointments',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, RouterModule, ReactiveFormsModule, FormsModule, MatDatepickerModule, SkeletonComponent],
  templateUrl: './appointments.html',
  providers: [
  { provide: MAT_DATE_LOCALE, useValue: 'ro-RO' },
  { provide: DateAdapter, useClass: MomentDateAdapter, deps: [MAT_DATE_LOCALE, MAT_MOMENT_DATE_ADAPTER_OPTIONS] },
  { provide: MAT_DATE_FORMATS, useValue: MY_DATE_FORMATS },
  ]
})

export class AppointmentsComponent implements OnInit {
  appointments: Appointment[] = [];
  filteredAppointments: Appointment[] = [];
  doctors: Doctor[] = [];
  patients: any[] = [];
  loading = true;
  saving = false;
  showForm = false;
  successMessage = '';
  errorMessage = '';
  currentRole = '';
  minDate = new Date();

  // ── Feature 8: Predicție slot-uri populare ────────────────────────────────
  popularSlots: any[] = [];
  loadingSlots = false;

  // Feature 5 — Heatmap
  weeklySlots: { date: string; day_label: string; slots: { time: string; booked: boolean }[] }[] = [];
  loadingHeatmap = false;
  heatmapWeekStart: string = '';   // YYYY-MM-DD

  // Recenzii
  reviewedAppointments = new Set<string>(); // appointment_id-uri deja recenzate
  showReviewDialog = false;
  reviewAppointmentId = '';
  reviewRating = 0;
  reviewHoverRating = 0;
  reviewComment = '';
  savingReview = false;

  // Filter state
  filterStatus  = 'all';
  filterDoctor  = 'all';
  filterDateFrom = '';
  filterDateTo   = '';
  filterDateFromMoment: any = null;
  filterDateToMoment:   any = null;
  sortOrder      = 'desc'; // 'asc' | 'desc'

  // Pagination
  currentPage = 0;
  readonly pageSize = 10;

  get displayedColumns(): string[] {
    if (this.currentRole === 'doctor') {
      return ['datetime', 'patient', 'reason', 'notes', 'actions'];
    }
    if (this.currentRole === 'admin' || this.currentRole === 'assistant') {
      return ['datetime', 'doctor', 'patient', 'reason', 'notes', 'actions'];
    }
    return ['datetime', 'doctor', 'status', 'reason', 'notes', 'actions'];
  }

  form: FormGroup;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private fb: FormBuilder,
  ) {
    this.form = this.fb.group({
      doctor_id: ['', Validators.required],
      date: ['', Validators.required],
      time: ['', Validators.required],
      notes: [''],
      reason: [''],
    });
  }

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      this.currentRole = user?.role || '';
      if (['doctor', 'admin', 'assistant'].includes(this.currentRole)) {
        this.apiService.get<any[]>('/patients/').subscribe({
          next: (data) => { this.patients = data; },
          error: () => {}
        });
      }
    });

    // Feature 8 — ascultă schimbarea doctorului în formular
    this.form.get('doctor_id')?.valueChanges.subscribe((doctorId: string) => {
      if (doctorId) {
        this.loadPopularSlots(doctorId);
        this.heatmapWeekStart = this._getMondayOfCurrentWeek();
        this.loadWeeklySlots(doctorId);
      } else {
        this.popularSlots = [];
        this.weeklySlots = [];
      }
    });

    this.apiService.get<Appointment[]>('/appointments/').subscribe({
      next: (data) => {
        this.appointments = data;
        this.applyFilters();
        this.loading = false;
        if (this.currentRole === 'patient') this.loadMyReviews();
      },
      error: () => { this.loading = false; }
    });

    this.apiService.get<Doctor[]>('/doctors/').subscribe({
      next: (data) => { this.doctors = data; },
      error: () => {}
    });
  }

  loadMyReviews(): void {
    this.apiService.get<any[]>('/reviews/my').subscribe({
      next: (reviews) => {
        reviews.forEach(r => this.reviewedAppointments.add(r.appointment_id));
      },
      error: () => {}
    });
  }

  openReviewDialog(appointmentId: string): void {
    this.reviewAppointmentId = appointmentId;
    this.reviewRating = 0;
    this.reviewHoverRating = 0;
    this.reviewComment = '';
    this.showReviewDialog = true;
  }

  closeReviewDialog(): void {
    this.showReviewDialog = false;
  }

  submitReview(): void {
    if (this.reviewRating === 0) return;
    this.savingReview = true;
    this.apiService.post('/reviews/', {
      appointment_id: this.reviewAppointmentId,
      rating: this.reviewRating,
      comment: this.reviewComment || null,
    }).subscribe({
      next: () => {
        this.reviewedAppointments.add(this.reviewAppointmentId);
        this.savingReview = false;
        this.showReviewDialog = false;
      },
      error: () => { this.savingReview = false; }
    });
  }

  getDoctorName(doctorId: string): string {
    const doctor = this.doctors.find(d => d.user_id === doctorId);
    return doctor ? ((doctor.first_name || doctor.last_name) ? `${doctor.first_name} ${doctor.last_name}` : doctor.email) : '-';
  }

  applyFilters(): void {
    let result = [...this.appointments];

    if (this.filterStatus !== 'all') {
      result = result.filter(a => a.status === this.filterStatus);
    }

    if (this.filterDoctor !== 'all') {
      result = result.filter(a => a.doctor_id === this.filterDoctor);
    }

    if (this.filterDateFrom) {
      const from = new Date(this.filterDateFrom);
      result = result.filter(a => new Date(a.datetime) >= from);
    }

    if (this.filterDateTo) {
      const to = new Date(this.filterDateTo);
      to.setHours(23, 59, 59, 999);
      result = result.filter(a => new Date(a.datetime) <= to);
    }

    result.sort((a, b) => {
      const diff = new Date(a.datetime).getTime() - new Date(b.datetime).getTime();
      return this.sortOrder === 'asc' ? diff : -diff;
    });

    this.filteredAppointments = result;
    this.currentPage = 0; // reset la pagina 1 la orice schimbare de filtru
  }

  get totalPages(): number {
    return Math.ceil(this.filteredAppointments.length / this.pageSize);
  }

  get pagedAppointments(): Appointment[] {
    const start = this.currentPage * this.pageSize;
    return this.filteredAppointments.slice(start, start + this.pageSize);
  }

  get pageNumbers(): number[] {
    return Array.from({ length: this.totalPages }, (_, i) => i);
  }

  goToPage(page: number): void {
    if (page >= 0 && page < this.totalPages) {
      this.currentPage = page;
    }
  }

  get pageStartIndex(): number {
    return this.filteredAppointments.length === 0 ? 0 : this.currentPage * this.pageSize + 1;
  }

  get pageEndIndex(): number {
    return Math.min((this.currentPage + 1) * this.pageSize, this.filteredAppointments.length);
  }

  onFilterDateFrom(e: any): void {
    this.filterDateFrom = e.value ? e.value.format('YYYY-MM-DD') : '';
    this.applyFilters();
  }

  onFilterDateTo(e: any): void {
    this.filterDateTo = e.value ? e.value.format('YYYY-MM-DD') : '';
    this.applyFilters();
  }

  resetFilters(): void {
    this.filterStatus        = 'all';
    this.filterDoctor        = 'all';
    this.filterDateFrom      = '';
    this.filterDateTo        = '';
    this.filterDateFromMoment = null;
    this.filterDateToMoment   = null;
    this.sortOrder           = 'desc';
    this.applyFilters();
  }

  get pendingCount()   { return this.appointments.filter(a => a.status === 'pending').length; }
  get confirmedCount() { return this.appointments.filter(a => a.status === 'confirmed').length; }
  get completedCount() { return this.appointments.filter(a => a.status === 'completed').length; }

  get activeFilterCount(): number {
    let count = 0;
    if (this.filterStatus  !== 'all') count++;
    if (this.filterDoctor  !== 'all') count++;
    if (this.filterDateFrom)          count++;
    if (this.filterDateTo)            count++;
    if (this.sortOrder !== 'desc')    count++;
    return count;
  }

  saveAppointment(): void {
    if (this.form.invalid) return;
    this.saving = true;
    this.successMessage = '';
    this.errorMessage = '';

    const dateValue = this.form.value.date;
    const timeStr = this.form.value.time;
    const dateStr = typeof dateValue === 'string' ? dateValue : dateValue.format('YYYY-MM-DD');
    const datetime = new Date(`${dateStr}T${timeStr}:00`);


    const payload = {
      doctor_id: this.form.value.doctor_id,
      datetime: datetime.toISOString(),
      notes: this.form.value.notes,
      reason: this.form.value.reason,
    };

    this.apiService.post<Appointment>('/appointments/', payload).subscribe({
      next: (newAppt) => {
        this.appointments = [newAppt, ...this.appointments];
        this.applyFilters();
        this.saving = false;
        this.successMessage = 'Programare creată cu succes!';
        this.showForm = false;
        this.form.reset();
      },
      error: () => {
        this.saving = false;
        this.errorMessage = 'Eroare la creare programare.';
      }
    });
  }

  private _getMondayOfCurrentWeek(): string {
    const d = new Date();
    const day = d.getDay(); // 0=Sun, 6=Sat
    if (day === 6) {
      // Sâmbătă → lunea viitoare
      d.setDate(d.getDate() + 2);
    } else if (day === 0) {
      // Duminică → lunea de mâine
      d.setDate(d.getDate() + 1);
    } else {
      // Luni–Vineri → lunea săptămânii curente
      d.setDate(d.getDate() - day + 1);
    }
    return d.toISOString().split('T')[0];
  }

  get minHeatmapWeekStart(): string {
    return this._getMondayOfCurrentWeek();
  }

  canGoPrevWeek(): boolean {
    return this.heatmapWeekStart > this.minHeatmapWeekStart;
  }

  loadWeeklySlots(doctorId: string): void {
    this.loadingHeatmap = true;
    this.apiService.get<any>(`/appointments/weekly-slots?doctor_id=${doctorId}&week_start=${this.heatmapWeekStart}`).subscribe({
      next: (data) => { this.weeklySlots = data.days || []; this.loadingHeatmap = false; },
      error: () => { this.loadingHeatmap = false; },
    });
  }

  prevWeek(doctorId: string): void {
    if (!this.canGoPrevWeek()) return;
    const d = new Date(this.heatmapWeekStart);
    d.setDate(d.getDate() - 7);
    this.heatmapWeekStart = d.toISOString().split('T')[0];
    this.loadWeeklySlots(doctorId);
  }

  nextWeek(doctorId: string): void {
    const d = new Date(this.heatmapWeekStart);
    d.setDate(d.getDate() + 7);
    this.heatmapWeekStart = d.toISOString().split('T')[0];
    this.loadWeeklySlots(doctorId);
  }

  applyHeatmapSlot(dateStr: string, timeStr: string): void {
    this.form.patchValue({ date: moment(dateStr, 'YYYY-MM-DD'), time: timeStr });
  }

  /** Feature 8 — încarcă slot-urile populare pentru doctorul selectat */
  loadPopularSlots(doctorId: string): void {
    this.loadingSlots = true;
    this.popularSlots = [];
    this.apiService.get<any[]>(`/appointments/popular-slots?doctor_id=${doctorId}`).subscribe({
      next: (slots) => {
        this.popularSlots = slots;
        this.loadingSlots = false;
      },
      error: () => { this.loadingSlots = false; }
    });
  }

  /**
   * Feature 8 — aplică un slot sugerat în formular.
   * Calculează următoarea apariție a zilei săptămânii din slot și
   * pre-completează câmpurile data și ora.
   */
  applySlot(slot: any): void {
    const today = new Date();
    const todayDow = today.getDay(); // 0=Dum, 1=Lun, ..., 6=Sâm (identic cu PostgreSQL DOW)
    let diff = slot.day_of_week - todayDow;
    if (diff <= 0) diff += 7; // mereu data viitoare
    const nextDate = new Date(today);
    nextDate.setDate(today.getDate() + diff);

    const timeStr = `${String(slot.hour).padStart(2, '0')}:00`;
    this.form.patchValue({
      date: moment(nextDate),
      time: timeStr,
    });
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

  updateStatus(appointmentId: string, status: string): void {
    this.apiService.patch<any>(`/appointments/${appointmentId}`, { status }).subscribe({
      next: () => {
        const index = this.appointments.findIndex(a => a.id === appointmentId);
        if (index !== -1) this.appointments[index] = { ...this.appointments[index], status };
        this.applyFilters();
      },
      error: () => {}
    });
  }

  cancelAppointment(appointmentId: string): void {
    this.apiService.patch<any>(`/appointments/${appointmentId}`, { status: 'cancelled' }).subscribe({
      next: () => {
        const index = this.appointments.findIndex(a => a.id === appointmentId);
        if (index !== -1) this.appointments[index] = { ...this.appointments[index], status: 'cancelled' };
        this.applyFilters();
      },
      error: () => {}
    });
  }

  getPatientName(patientId: string): string {
    const patient = this.patients.find(p => p.id === patientId);
    return patient ? ((patient.first_name || patient.last_name) ? `${patient.first_name} ${patient.last_name}` : patient.email) : '-';
  } 
}
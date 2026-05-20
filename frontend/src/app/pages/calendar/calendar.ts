import { Component, OnInit, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { FullCalendarModule, FullCalendarComponent } from '@fullcalendar/angular';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { ThemeService } from '../../services/theme';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AppointmentDetailDialogComponent } from './appointment-detail-dialog.component';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'app-calendar',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, FullCalendarModule, MatDialogModule],
  templateUrl: './calendar.html',
})
export class CalendarComponent implements OnInit, OnDestroy {
  @ViewChild('calendar') calendarComponent!: FullCalendarComponent;

  doctors: any[] = [];
  allEvents: EventInput[] = [];
  isAdmin = false;
  isDark = false;
  loading = true;

  private destroy$ = new Subject<void>();

  // ── Stats getters ──────────────────────────────────────────────────────────
  get totalCount()     { return this.allEvents.length; }
  get pendingCount()   { return this.allEvents.filter(e => (e as any).extendedProps?.status === 'pending').length; }
  get confirmedCount() { return this.allEvents.filter(e => (e as any).extendedProps?.status === 'confirmed').length; }
  get completedCount() { return this.allEvents.filter(e => (e as any).extendedProps?.status === 'completed').length; }
  get cancelledCount() { return this.allEvents.filter(e => (e as any).extendedProps?.status === 'cancelled').length; }

  calendarOptions: CalendarOptions = {
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    locale: 'ro',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay',
    },
    buttonText: {
      today: 'Azi',
      month: 'Lună',
      week: 'Săptămână',
      day: 'Zi',
    },
    nowIndicator: true,
    slotMinTime: '07:00:00',
    slotMaxTime: '21:00:00',
    scrollTime: '08:00:00',
    allDaySlot: false,
    height: 'auto',
    eventContent: (arg) => this.buildEventContent(arg),
    eventClick: this.handleEventClick.bind(this),
    events: [],
  };

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    public themeService: ThemeService,
    private dialog: MatDialog,
  ) {
    this.isAdmin = this.authService.getCurrentUser()?.role === 'admin';
  }

  ngOnInit(): void {
    // Urmărește dark mode
    this.themeService.isDark$
      .pipe(takeUntil(this.destroy$))
      .subscribe(dark => { this.isDark = dark; });

    this.apiService.get<any[]>('/doctors/').subscribe({
      next: (doctors) => { this.doctors = doctors; this.loadAppointments(); },
      error: ()        => { this.loadAppointments(); },
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadAppointments(): void {
    this.loading = true;
    this.apiService.get<any[]>('/appointments/').subscribe({
      next: (appointments) => {
        const events: EventInput[] = appointments.map(a => {
          const doctor = this.doctors.find(d => d.user_id === a.doctor_id);
          const doctorName = doctor
            ? ((doctor.first_name || doctor.last_name)
                ? `${doctor.first_name || ''} ${doctor.last_name || ''}`.trim()
                : doctor.email)
            : '';
          return {
            id: a.id,
            title: doctorName,
            start: a.datetime,
            backgroundColor: 'transparent',
            borderColor: 'transparent',
            extendedProps: { ...a, doctorName },
          };
        });
        this.allEvents = events;
        this.calendarOptions = { ...this.calendarOptions, events: [...events] };
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  filterByDoctor(doctorId: string): void {
    const filtered = doctorId === 'all'
      ? this.allEvents
      : this.allEvents.filter(e => (e as any).extendedProps?.doctor_id === doctorId);
    this.calendarOptions = { ...this.calendarOptions, events: [...filtered] };
  }

  handleEventClick(info: any): void {
    const ref = this.dialog.open(AppointmentDetailDialogComponent, {
      width: '480px',
      data: info.event.extendedProps,
    });
    ref.afterClosed().subscribe(result => {
      if (!result?.updated) return;
      const calApi = this.calendarComponent.getApi();
      const event = calApi.getEventById(result.id);
      if (event) {
        event.setExtendedProp('status', result.status);
        // Rerender event cu noua culoare
        const newEvents = this.allEvents.map(e =>
          (e.id === result.id)
            ? { ...e, extendedProps: { ...(e as any).extendedProps, status: result.status } }
            : e
        );
        this.allEvents = newEvents;
        this.calendarOptions = { ...this.calendarOptions, events: [...newEvents] };
      }
    });
  }

  // ── Event pill content ─────────────────────────────────────────────────────

  buildEventContent(arg: any): { html: string } {
    const status   = arg.event.extendedProps['status'] as string;
    const doctor   = arg.event.extendedProps['doctorName'] as string || '';
    const time     = arg.event.start
      ? new Date(arg.event.start).toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' })
      : '';
    const color    = this.getStatusColor(status);
    const bg       = this.getStatusBg(status);
    const short    = doctor.length > 20 ? doctor.slice(0, 18) + '…' : doctor;

    return { html: `
      <div class="fc-pill" style="border-left-color:${color};background:${bg};">
        <div class="fc-pill-time" style="color:${color};">${time}</div>
        <div class="fc-pill-name">${short || '—'}</div>
      </div>` };
  }

  getStatusColor(status: string): string {
    const map: Record<string, string> = {
      pending:   '#f59e0b',
      confirmed: '#2563eb',
      completed: '#16a34a',
      cancelled: '#dc2626',
    };
    return map[status] ?? '#2563eb';
  }

  getStatusBg(status: string): string {
    const map: Record<string, string> = {
      pending:   '#fffbeb',
      confirmed: '#eff6ff',
      completed: '#f0fdf4',
      cancelled: '#fef2f2',
    };
    return map[status] ?? '#eff6ff';
  }

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      pending: 'În așteptare', confirmed: 'Confirmat',
      completed: 'Finalizat',  cancelled: 'Anulat',
    };
    return map[status] ?? status;
  }
}

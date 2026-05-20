import { FormBuilder } from '@angular/forms';
import { AppointmentsComponent } from './appointments';
import { Subject } from 'rxjs';

function makeAppointment(status: string, doctorId = 'd1', daysOffset = 0) {
  const d = new Date();
  d.setDate(d.getDate() + daysOffset);
  return {
    id: Math.random().toString(),
    patient_id: 'p1',
    doctor_id: doctorId,
    datetime: d.toISOString(),
    status,
    notes: 'note',
    reason: 'reason',
  };
}

describe('AppointmentsComponent — logică business', () => {
  let component: AppointmentsComponent;
  const apiSpy = jasmine.createSpyObj('ApiService', ['get', 'post', 'patch']);
  const authSpy = { currentUser$: new Subject<any>() } as any;
  const fb = new FormBuilder();

  beforeEach(() => {
    component = new AppointmentsComponent(apiSpy as any, authSpy, fb);
    component.appointments = [
      makeAppointment('pending', 'd1', 1),
      makeAppointment('confirmed', 'd1', 2),
      makeAppointment('confirmed', 'd2', 3),
      makeAppointment('cancelled', 'd1', -1),
      makeAppointment('completed', 'd2', -2),
    ];
    component.filteredAppointments = [...component.appointments];
  });

  // ── displayedColumns per rol ──────────────────────────────────────────────

  it('patient should see datetime, doctor, status, reason, notes, actions columns', () => {
    component.currentRole = 'patient';
    expect(component.displayedColumns).toEqual(['datetime', 'doctor', 'status', 'reason', 'notes', 'actions']);
  });

  it('doctor should see datetime, patient, reason, notes, actions columns', () => {
    component.currentRole = 'doctor';
    expect(component.displayedColumns).toContain('patient');
    expect(component.displayedColumns).not.toContain('doctor');
  });

  it('admin should see all columns including doctor and patient', () => {
    component.currentRole = 'admin';
    expect(component.displayedColumns).toContain('doctor');
    expect(component.displayedColumns).toContain('patient');
  });

  it('assistant should see same columns as admin', () => {
    component.currentRole = 'assistant';
    expect(component.displayedColumns).toContain('doctor');
    expect(component.displayedColumns).toContain('patient');
  });

  // ── applyFilters — filtrare după status ───────────────────────────────────

  it('filterStatus all returns all appointments', () => {
    component.filterStatus = 'all';
    component.applyFilters();
    expect(component.filteredAppointments.length).toBe(5);
  });

  it('filterStatus pending returns only pending', () => {
    component.filterStatus = 'pending';
    component.applyFilters();
    expect(component.filteredAppointments.length).toBe(1);
    expect(component.filteredAppointments[0].status).toBe('pending');
  });

  it('filterStatus confirmed returns only confirmed', () => {
    component.filterStatus = 'confirmed';
    component.applyFilters();
    expect(component.filteredAppointments.length).toBe(2);
  });

  it('filterStatus cancelled returns only cancelled', () => {
    component.filterStatus = 'cancelled';
    component.applyFilters();
    expect(component.filteredAppointments.length).toBe(1);
  });

  // ── applyFilters — filtrare după doctor ───────────────────────────────────

  it('filterDoctor by d1 returns only d1 appointments', () => {
    component.filterStatus = 'all';
    component.filterDoctor = 'd1';
    component.applyFilters();
    component.filteredAppointments.forEach(a => expect(a.doctor_id).toBe('d1'));
  });

  it('filterDoctor all returns all', () => {
    component.filterDoctor = 'all';
    component.applyFilters();
    expect(component.filteredAppointments.length).toBe(5);
  });

  // ── applyFilters — sortare ────────────────────────────────────────────────

  it('sortOrder desc returns newest-first', () => {
    component.filterStatus = 'all';
    component.filterDoctor = 'all';
    component.sortOrder = 'desc';
    component.applyFilters();
    const dates = component.filteredAppointments.map(a => new Date(a.datetime).getTime());
    for (let i = 1; i < dates.length; i++) {
      expect(dates[i]).toBeLessThanOrEqual(dates[i - 1]);
    }
  });

  it('sortOrder asc returns oldest-first', () => {
    component.filterStatus = 'all';
    component.filterDoctor = 'all';
    component.sortOrder = 'asc';
    component.applyFilters();
    const dates = component.filteredAppointments.map(a => new Date(a.datetime).getTime());
    for (let i = 1; i < dates.length; i++) {
      expect(dates[i]).toBeGreaterThanOrEqual(dates[i - 1]);
    }
  });

  // ── Paginare ──────────────────────────────────────────────────────────────

  it('totalPages with 5 items and pageSize=10 is 1', () => {
    component.filteredAppointments = Array.from({ length: 5 }, () => makeAppointment('pending'));
    expect(component.totalPages).toBe(1);
  });

  it('totalPages with 15 items and pageSize=10 is 2', () => {
    component.filteredAppointments = Array.from({ length: 15 }, () => makeAppointment('pending'));
    expect(component.totalPages).toBe(2);
  });

  it('pagedAppointments returns max pageSize items', () => {
    component.filteredAppointments = Array.from({ length: 15 }, () => makeAppointment('pending'));
    component.currentPage = 0;
    expect(component.pagedAppointments.length).toBe(10);
  });

  it('pagedAppointments page 2 returns remaining items', () => {
    component.filteredAppointments = Array.from({ length: 15 }, () => makeAppointment('pending'));
    component.currentPage = 1;
    expect(component.pagedAppointments.length).toBe(5);
  });

  it('goToPage changes currentPage', () => {
    component.filteredAppointments = Array.from({ length: 25 }, () => makeAppointment('pending'));
    component.goToPage(1);
    expect(component.currentPage).toBe(1);
  });

  it('goToPage ignores out-of-bounds pages', () => {
    component.filteredAppointments = Array.from({ length: 5 }, () => makeAppointment('pending'));
    component.currentPage = 0;
    component.goToPage(5); // out of bounds
    expect(component.currentPage).toBe(0);
  });

  // ── Formular ──────────────────────────────────────────────────────────────

  it('form should be invalid when empty', () => {
    expect(component.form.invalid).toBeTrue();
  });

  it('form should be valid when doctor_id, date, time filled', () => {
    component.form.patchValue({ doctor_id: 'd1', date: '2030-01-01', time: '10:00' });
    expect(component.form.valid).toBeTrue();
  });

  it('form should be invalid without doctor_id', () => {
    component.form.patchValue({ date: '2030-01-01', time: '10:00' });
    expect(component.form.invalid).toBeTrue();
  });

  // ── getDoctorName ─────────────────────────────────────────────────────────

  it('getDoctorName returns - for unknown doctor', () => {
    component.doctors = [];
    expect(component.getDoctorName('unknown-id')).toBe('-');
  });

  it('getDoctorName returns full name when available', () => {
    component.doctors = [
      { id: 'd1', user_id: 'u1', email: 'dr@test.com', first_name: 'Ion', last_name: 'Pop', specialization: 'Gen' }
    ];
    expect(component.getDoctorName('u1')).toBe('Ion Pop');
  });

  it('getDoctorName falls back to email when no name', () => {
    component.doctors = [
      { id: 'd1', user_id: 'u1', email: 'dr@test.com', specialization: 'Gen' }
    ];
    expect(component.getDoctorName('u1')).toBe('dr@test.com');
  });

  // ── resetFilters ──────────────────────────────────────────────────────────

  it('resetFilters should reset all filter state', () => {
    component.filterStatus = 'confirmed';
    component.filterDoctor = 'd1';
    component.sortOrder = 'asc';
    component.resetFilters();
    expect(component.filterStatus).toBe('all');
    expect(component.filterDoctor).toBe('all');
    expect(component.sortOrder).toBe('desc');
  });
});

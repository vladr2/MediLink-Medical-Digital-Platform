import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';
import { NotificationService } from '../../services/notification';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface Medication {
  name: string;
  dose: string;
  frequency: string;
  duration: string;
  notes?: string;
}

interface Prescription {
  id: string;
  patient_id: string;
  doctor_id: string;
  appointment_id: string | null;
  medications: Medication[];
  notes: string | null;
  issued_at: string | null;
  doctor_name: string | null;
  patient_name: string | null;
}

interface Patient {
  id: string;
  user_id: string;
  first_name?: string;
  last_name?: string;
  email: string;
}

interface PrescriptionTemplate {
  id: string;
  name: string;
  medications: Medication[];
  notes: string | null;
}

@Component({
  selector: 'app-prescriptions',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, FormsModule, SkeletonComponent],
  templateUrl: './prescriptions.html',
})
export class PrescriptionsComponent implements OnInit {
  prescriptions: Prescription[] = [];
  loading = true;
  currentRole = '';
  expandedId: string | null = null;

  // Doctor: formular emitere prescripție
  showForm = false;
  patients: Patient[] = [];
  newRx = {
    patient_id: '',
    appointment_id: null as string | null,
    notes: '',
    medications: [this.emptyMed()],
  };
  saving = false;

  // Feature 9: Template-uri rețetă
  templates: PrescriptionTemplate[] = [];
  loadingTemplates = false;
  showSaveTemplateInput = false;
  newTemplateName = '';
  savingTemplate = false;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private notification: NotificationService,
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      this.currentRole = user?.role || '';
    });

    const endpoint = this.authService.getCurrentUser()?.role === 'doctor'
      ? '/prescriptions/doctor'
      : '/prescriptions/my';

    this.apiService.get<Prescription[]>(endpoint).subscribe({
      next: (data) => { this.prescriptions = data; this.loading = false; },
      error: () => { this.loading = false; }
    });

    if (this.authService.getCurrentUser()?.role === 'doctor') {
      this.apiService.get<any[]>('/patients/').subscribe({
        next: (data) => { this.patients = data; },
        error: () => {}
      });
      this.loadTemplates();
    }
  }

  loadTemplates(): void {
    this.loadingTemplates = true;
    this.apiService.get<PrescriptionTemplate[]>('/prescriptions/templates').subscribe({
      next: (data) => { this.templates = data; this.loadingTemplates = false; },
      error: () => { this.loadingTemplates = false; }
    });
  }

  applyTemplate(template: PrescriptionTemplate): void {
    this.newRx.medications = template.medications.map(m => ({ ...m }));
    if (template.notes) this.newRx.notes = template.notes;
  }

  saveAsTemplate(): void {
    if (!this.newTemplateName.trim()) return;
    this.savingTemplate = true;
    this.apiService.post<any>('/prescriptions/templates', {
      name: this.newTemplateName.trim(),
      medications: this.newRx.medications,
      notes: this.newRx.notes || null,
    }).subscribe({
      next: (t) => {
        this.templates.unshift({ id: t.id, name: this.newTemplateName.trim(), medications: this.newRx.medications, notes: this.newRx.notes || null });
        this.newTemplateName = '';
        this.showSaveTemplateInput = false;
        this.savingTemplate = false;
        this.notification.success('Template salvat!');
      },
      error: () => {
        this.savingTemplate = false;
        this.notification.error('Eroare la salvarea template-ului.');
      }
    });
  }

  deleteTemplate(id: string): void {
    this.apiService.delete(`/prescriptions/templates/${id}`).subscribe({
      next: () => {
        this.templates = this.templates.filter(t => t.id !== id);
        this.notification.success('Template șters.');
      },
      error: () => this.notification.error('Eroare la ștergerea template-ului.')
    });
  }

  emptyMed(): Medication {
    return { name: '', dose: '', frequency: '', duration: '', notes: '' };
  }

  addMedication(): void {
    this.newRx.medications.push(this.emptyMed());
  }

  removeMedication(i: number): void {
    if (this.newRx.medications.length > 1) {
      this.newRx.medications.splice(i, 1);
    }
  }

  savePrescription(): void {
    if (!this.newRx.patient_id || this.newRx.medications.some(m => !m.name || !m.dose)) {
      this.notification.error('Completează pacientul și toate câmpurile obligatorii ale medicamentelor.');
      return;
    }
    this.saving = true;
    this.apiService.post<Prescription>('/prescriptions/', {
      patient_id: this.newRx.patient_id,
      appointment_id: this.newRx.appointment_id || null,
      medications: this.newRx.medications,
      notes: this.newRx.notes || null,
    }).subscribe({
      next: (rx) => {
        this.prescriptions.unshift(rx);
        this.showForm = false;
        this.newRx = { patient_id: '', appointment_id: null, notes: '', medications: [this.emptyMed()] };
        this.saving = false;
        this.notification.success('Prescripție emisă cu succes!');
      },
      error: () => {
        this.saving = false;
        this.notification.error('Eroare la emiterea prescripției.');
      }
    });
  }

  toggleExpand(id: string): void {
    this.expandedId = this.expandedId === id ? null : id;
  }

  exportPdf(id: string): void {
    const token = localStorage.getItem('access_token');
    fetch(`/api/prescriptions/${id}/export`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const win = window.open(url, '_blank');
      if (!win) this.notification.error('Permite pop-up-urile pentru export.');
      setTimeout(() => URL.revokeObjectURL(url), 120000);
    })
    .catch(() => this.notification.error('Eroare la export.'));
  }

  getPatientName(p: Patient): string {
    const name = `${p.first_name || ''} ${p.last_name || ''}`.trim();
    return name || p.email;
  }
}

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface MedicalRecord {
  id: string;
  patient_id: string;
  doctor_id: string;
  record_type: string;
  notes_encrypted: string;
  diagnosis?: string;
  treatment?: string;
  analysis_result?: string;
  created_at: string;
  has_anomaly?: boolean | null;
  anomaly_notes?: string | null;
}

@Component({
  selector: 'app-medical-records',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './medical-records.html',
})
export class MedicalRecordsComponent implements OnInit {
  records: MedicalRecord[] = [];
  loading = true;
  searchText = '';
  expandedId: string | null = null;

  // ── AI Summary ──────────────────────────────────────────────────────────────
  aiSummary: string | null = null;
  aiGeneratedAt: string | null = null;
  aiRecordCount = 0;
  loadingAI = false;
  showAISummary = false;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.apiService.get<any>('/patients/me').subscribe({
      next: (patient) => this.loadRecords(patient.id),
      error: () => { this.loading = false; },
    });
  }

  loadRecords(patientId: string): void {
    this.apiService.get<MedicalRecord[]>(`/medical-records/patient/${patientId}`).subscribe({
      next: (data) => {
        this.records = data.sort((a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  get filtered(): MedicalRecord[] {
    const q = this.searchText.trim().toLowerCase();
    if (!q) return this.records;
    return this.records.filter(r =>
      (r.diagnosis        || '').toLowerCase().includes(q) ||
      (r.treatment        || '').toLowerCase().includes(q) ||
      (r.analysis_result  || '').toLowerCase().includes(q) ||
      (r.notes_encrypted  || '').toLowerCase().includes(q) ||
      this.typeLabel(r.record_type).toLowerCase().includes(q)
    );
  }

  get countConsultatie() { return this.records.filter(r => r.record_type === 'consultatie').length; }
  get countAnaliza()     { return this.records.filter(r => r.record_type === 'analiza').length; }
  get countTratament()   { return this.records.filter(r => r.record_type === 'tratament').length; }

  toggleExpand(id: string): void {
    this.expandedId = this.expandedId === id ? null : id;
  }

  typeLabel(type: string): string {
    const m: Record<string, string> = {
      consultatie: 'Consultație', analiza: 'Analiză', tratament: 'Tratament',
    };
    return m[type] || type;
  }

  typeColor(type: string): string {
    const m: Record<string, string> = {
      consultatie: '#2563eb', analiza: '#0d9488', tratament: '#ea580c',
    };
    return m[type] ?? '#2563eb';
  }

  typeBg(type: string): string {
    const m: Record<string, string> = {
      consultatie: '#eff6ff', analiza: '#f0fdfa', tratament: '#fff7ed',
    };
    return m[type] ?? '#eff6ff';
  }

  typeIcon(type: string): string {
    const m: Record<string, string> = {
      consultatie: 'stethoscope', analiza: 'microscope', tratament: 'pill',
    };
    return m[type] ?? 'notes-medical';
  }

  generateAISummary(): void {
    this.loadingAI = true;
    this.aiSummary = null;
    this.showAISummary = true;
    this.apiService.get<any>('/patients/me/ai-summary').subscribe({
      next: (data) => {
        this.aiSummary = data.summary;
        this.aiGeneratedAt = data.generated_at;
        this.aiRecordCount = data.record_count;
        this.loadingAI = false;
      },
      error: () => {
        this.aiSummary = 'Eroare la generarea sumarului. Încearcă din nou.';
        this.loadingAI = false;
      },
    });
  }
}

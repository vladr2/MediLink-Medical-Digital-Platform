import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface Treatment {
  id: string;
  patient_id: string;
  doctor_id: string;
  record_type: string;
  notes_encrypted: string;
  diagnosis: string;
  treatment: string;
  analysis_result: string;
  created_at: string;
}

@Component({
  selector: 'app-treatments',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './treatments.html',
})
export class TreatmentsComponent implements OnInit {
  treatments: Treatment[] = [];
  loading = true;
  searchText = '';
  expandedId: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.apiService.get<any>('/patients/me').subscribe({
      next: (patient) => this.loadData(patient.id),
      error: () => { this.loading = false; },
    });
  }

  loadData(patientId: string): void {
    this.apiService.get<Treatment[]>(`/medical-records/patient/${patientId}`).subscribe({
      next: (data) => {
        this.treatments = data
          .filter(r => r.record_type === 'tratament')
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  get filtered(): Treatment[] {
    const q = this.searchText.trim().toLowerCase();
    if (!q) return this.treatments;
    return this.treatments.filter(t =>
      (t.treatment       || '').toLowerCase().includes(q) ||
      (t.diagnosis       || '').toLowerCase().includes(q) ||
      (t.notes_encrypted || '').toLowerCase().includes(q)
    );
  }

  get lastDate(): string {
    if (!this.treatments.length) return '—';
    return new Date(this.treatments[0].created_at).toLocaleDateString('ro-RO', {
      day: '2-digit', month: 'long', year: 'numeric',
    });
  }

  toggleExpand(id: string): void {
    this.expandedId = this.expandedId === id ? null : id;
  }

  isRecent(dateStr: string): boolean {
    const diff = (Date.now() - new Date(dateStr).getTime()) / (1000 * 60 * 60 * 24);
    return diff <= 30;
  }
}

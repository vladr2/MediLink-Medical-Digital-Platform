import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface Analysis {
  id: string;
  patient_id: string;
  record_type: string;
  notes_encrypted: string;
  analysis_result: string;
  diagnosis: string;
  created_at: string;
  has_anomaly?: boolean | null;
  anomaly_notes?: string | null;
}

@Component({
  selector: 'app-analyses',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './analyses.html',
})
export class AnalysesComponent implements OnInit {
  analyses: Analysis[] = [];
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
    this.apiService.get<Analysis[]>(`/medical-records/patient/${patientId}`).subscribe({
      next: (data) => {
        this.analyses = data
          .filter(r => r.record_type === 'analiza')
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  get filtered(): Analysis[] {
    const q = this.searchText.trim().toLowerCase();
    if (!q) return this.analyses;
    return this.analyses.filter(a =>
      (a.analysis_result || '').toLowerCase().includes(q) ||
      (a.notes_encrypted  || '').toLowerCase().includes(q) ||
      (a.diagnosis        || '').toLowerCase().includes(q)
    );
  }

  get lastDate(): string {
    if (!this.analyses.length) return '—';
    return new Date(this.analyses[0].created_at).toLocaleDateString('ro-RO', {
      day: '2-digit', month: 'long', year: 'numeric',
    });
  }

  toggleExpand(id: string): void {
    this.expandedId = this.expandedId === id ? null : id;
  }

  isRecent(dateStr: string): boolean {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24);
    return diff <= 30;
  }
}

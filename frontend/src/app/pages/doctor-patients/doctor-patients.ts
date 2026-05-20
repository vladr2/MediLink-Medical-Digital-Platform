import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface Patient {
  id: string;
  user_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  blood_type: string;
  allergies: string;
  chronic_conditions: string;
  is_active: boolean;
}

@Component({
  selector: 'app-doctor-patients',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './doctor-patients.html',
})
export class DoctorPatientsComponent implements OnInit {
  patients: Patient[] = [];
  filteredPatients: Patient[] = [];
  loading = true;
  searchText = '';

  displayedColumns = ['full_name', 'blood_type', 'allergies', 'chronic_conditions'];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.apiService.get<Patient[]>('/doctors/my-patients').subscribe({
      next: (data) => {
        this.patients = data;
        this.filteredPatients = data;
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  filterPatients(): void {
    const q = this.searchText.trim().toLowerCase();
    this.filteredPatients = q
      ? this.patients.filter(p =>
          `${p.first_name || ''} ${p.last_name || ''} ${p.email}`.toLowerCase().includes(q)
        )
      : this.patients;
  }

  patientName(p: Patient): string {
    const n = `${p.first_name || ''} ${p.last_name || ''}`.trim();
    return n || p.email;
  }
}

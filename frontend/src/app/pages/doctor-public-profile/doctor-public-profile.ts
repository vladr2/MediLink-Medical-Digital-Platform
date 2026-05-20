import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface DoctorProfile {
  id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  specialization: string;
  department: string;
  bio: string;
  schedule: string;
  phone_cabinet: string;
  license_number: string;
}

interface Review {
  id: string;
  rating: number;
  comment: string | null;
  sentiment: 'pozitiv' | 'negativ' | 'neutru' | null;
  created_at: string | null;
  patient_name: string | null;
}

@Component({
  selector: 'app-doctor-public-profile',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './doctor-public-profile.html',
})
export class DoctorPublicProfileComponent implements OnInit {
  doctor: DoctorProfile | null = null;
  reviews: Review[] = [];
  loading = true;
  notFound = false;

  get avgRating(): number {
    if (!this.reviews.length) return 0;
    return Math.round(this.reviews.reduce((s, r) => s + r.rating, 0) / this.reviews.length * 10) / 10;
  }

  get starsArray(): number[] { return [1, 2, 3, 4, 5]; }

  // Feature 14 — statistici sentiment
  get sentimentStats(): { pozitiv: number; neutru: number; negativ: number } {
    const withSentiment = this.reviews.filter(r => r.sentiment);
    return {
      pozitiv: withSentiment.filter(r => r.sentiment === 'pozitiv').length,
      neutru:  withSentiment.filter(r => r.sentiment === 'neutru').length,
      negativ: withSentiment.filter(r => r.sentiment === 'negativ').length,
    };
  }

  sentimentLabel(s: string | null): string {
    if (s === 'pozitiv') return '😊 Pozitiv';
    if (s === 'negativ') return '😞 Negativ';
    if (s === 'neutru')  return '😐 Neutru';
    return '';
  }

  sentimentColor(s: string | null): string {
    if (s === 'pozitiv') return '#16a34a';
    if (s === 'negativ') return '#dc2626';
    if (s === 'neutru')  return '#ca8a04';
    return '#94a3b8';
  }

  sentimentBg(s: string | null): string {
    if (s === 'pozitiv') return '#dcfce7';
    if (s === 'negativ') return '#fee2e2';
    if (s === 'neutru')  return '#fef9c3';
    return '#f1f5f9';
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
  ) {}

  ngOnInit(): void {
    const userId = this.route.snapshot.paramMap.get('id');
    if (!userId) { this.notFound = true; this.loading = false; return; }

    this.apiService.get<DoctorProfile>(`/doctors/by-user/${userId}`).subscribe({
      next: (doc) => {
        this.doctor = doc;
        this.loading = false;
        this.apiService.get<Review[]>(`/reviews/doctor/${userId}`).subscribe({
          next: (r) => { this.reviews = r; },
          error: () => {}
        });
      },
      error: () => {
        this.notFound = true;
        this.loading = false;
      },
    });
  }

  getInitials(): string {
    if (!this.doctor) return '?';
    const f = this.doctor.first_name?.trim();
    const l = this.doctor.last_name?.trim();
    if (f && l) return (f[0] + l[0]).toUpperCase();
    if (f)      return f.slice(0, 2).toUpperCase();
    if (l)      return l.slice(0, 2).toUpperCase();
    return this.doctor.email?.slice(0, 2).toUpperCase() ?? '?';
  }

  getFullName(): string {
    if (!this.doctor) return '';
    const name = `${this.doctor.first_name || ''} ${this.doctor.last_name || ''}`.trim();
    return name || this.doctor.email;
  }

  goBack(): void {
    this.router.navigate(['/dashboard/appointments']);
  }
}

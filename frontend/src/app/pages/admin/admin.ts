import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';

interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  first_name?: string;
  last_name?: string;
}

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './admin.html',
})
export class AdminComponent implements OnInit {
  users: User[] = [];
  loading = true;
  displayedColumns = ['email', 'full_name', 'role', 'is_active', 'created_at', 'actions'];

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.apiService.get<User[]>('/users/').subscribe({
      next: (data) => {
        this.users = data;
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }

  toggleActive(user: User): void {
    this.apiService.patch<User>(`/users/${user.id}/toggle-active`, {}).subscribe({
      next: (updated) => {
        const index = this.users.findIndex(u => u.id === user.id);
        if (index !== -1) this.users[index] = updated;
      },
      error: () => {}
    });
  }

  getRoleColor(role: string): string {
    const colors: any = {
      admin: 'warn',
      doctor: 'primary',
      assistant: 'accent',
      patient: ''
    };
    return colors[role] || '';
  }
  get activeUsers(): number {
    return this.users.filter(u => u.is_active).length;
  }

  get doctorCount(): number {
    return this.users.filter(u => u.role === 'doctor').length;
  }

  get patientCount(): number {
    return this.users.filter(u => u.role === 'patient').length;
  }
}

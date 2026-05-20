import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { MatDialogRef, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { ApiService } from '../../services/api';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-appointment-detail-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, MatDialogModule, TablerIconsModule],
  template: `
    <!-- Header cu status color -->
    <div [style.background]="statusBg" style="padding:20px 24px 16px; border-radius:4px 4px 0 0;">
      <div style="display:flex; align-items:center; gap:10px;">
        <div [style.background]="statusColor"
             style="width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;">
          <i-tabler [name]="statusIcon" style="color:#fff;width:22px;height:22px;"></i-tabler>
        </div>
        <div>
          <h2 mat-dialog-title style="margin:0;font-size:1rem;font-weight:700;">Detalii programare</h2>
          <p style="margin:2px 0 0;font-size:.8rem;color:#64748b;">
            {{ data.datetime | date:'EEEE, d MMMM yyyy':'':'ro' }} la ora {{ data.datetime | date:'HH:mm' }}
          </p>
        </div>
        <span style="flex:1"></span>
        <span [style.background]="statusColor"
              style="padding:3px 10px;border-radius:20px;color:#fff;font-size:.75rem;font-weight:700;white-space:nowrap;">
          {{ statusLabel }}
        </span>
      </div>
    </div>

    <mat-dialog-content style="padding:20px 24px; min-width:420px;">
      <div style="display:flex;flex-direction:column;gap:14px;">

        <!-- Doctor -->
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <div style="width:36px;height:36px;border-radius:8px;background:#eff6ff;
                      display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <i-tabler name="stethoscope" style="color:#2563eb;width:18px;height:18px;"></i-tabler>
          </div>
          <div>
            <p style="margin:0;font-size:.73rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;">Doctor</p>
            <p style="margin:2px 0 0;font-weight:600;color:#1e293b;">Dr. {{ data.doctorName || '—' }}</p>
          </div>
        </div>

        <!-- Motiv -->
        <div *ngIf="data.reason" style="display:flex;gap:12px;align-items:flex-start;">
          <div style="width:36px;height:36px;border-radius:8px;background:#f0fdf4;
                      display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <i-tabler name="clipboard-text" style="color:#16a34a;width:18px;height:18px;"></i-tabler>
          </div>
          <div>
            <p style="margin:0;font-size:.73rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;">Motiv consultație</p>
            <p style="margin:2px 0 0;color:#1e293b;">{{ data.reason }}</p>
          </div>
        </div>

        <!-- Note -->
        <div *ngIf="data.notes" style="display:flex;gap:12px;align-items:flex-start;">
          <div style="width:36px;height:36px;border-radius:8px;background:#fff8f0;
                      display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <i-tabler name="notes" style="color:#f59e0b;width:18px;height:18px;"></i-tabler>
          </div>
          <div>
            <p style="margin:0;font-size:.73rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;">Note</p>
            <p style="margin:2px 0 0;color:#1e293b;">{{ data.notes }}</p>
          </div>
        </div>

        <!-- Separator -->
        <mat-divider *ngIf="canChangeStatus"></mat-divider>

        <!-- Schimbare status (staff) -->
        <div *ngIf="canChangeStatus">
          <p style="margin:0 0 8px;font-size:.82rem;font-weight:700;color:#475569;">
            <i-tabler name="edit" style="width:15px;height:15px;vertical-align:middle;margin-right:4px;"></i-tabler>
            Actualizează status
          </p>
          <mat-form-field appearance="outline" class="w-100" subscriptSizing="dynamic">
            <mat-select [(value)]="currentStatus" (selectionChange)="updateStatus($event.value)">
              <mat-option value="pending">⏳ În așteptare</mat-option>
              <mat-option value="confirmed">✅ Confirmat</mat-option>
              <mat-option value="completed">🏁 Finalizat</mat-option>
              <mat-option value="cancelled">❌ Anulat</mat-option>
            </mat-select>
          </mat-form-field>
          <p *ngIf="saved" style="margin:8px 0 0;color:#16a34a;font-size:.82rem;font-weight:600;">
            <i-tabler name="circle-check" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i-tabler>
            Status actualizat cu succes!
          </p>
        </div>

      </div>
    </mat-dialog-content>

    <mat-dialog-actions align="end" style="padding:12px 24px;">
      <button mat-flat-button color="primary" mat-dialog-close style="border-radius:8px;">
        Închide
      </button>
    </mat-dialog-actions>
  `,
})
export class AppointmentDetailDialogComponent {
  currentStatus: string;
  saved = false;
  canChangeStatus = false;

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: any,
    private dialogRef: MatDialogRef<AppointmentDetailDialogComponent>,
    private apiService: ApiService,
    private authService: AuthService,
  ) {
    this.currentStatus = data.status;
    const role = this.authService.getCurrentUser()?.role;
    this.canChangeStatus = (role === 'doctor' || role === 'admin' || role === 'assistant')
      && this.currentStatus !== 'completed' && this.currentStatus !== 'cancelled';
  }

  get statusColor(): string {
    const m: Record<string, string> = {
      pending: '#f59e0b', confirmed: '#2563eb',
      completed: '#16a34a', cancelled: '#dc2626',
    };
    return m[this.currentStatus] ?? '#2563eb';
  }

  get statusBg(): string {
    const m: Record<string, string> = {
      pending: '#fffbeb', confirmed: '#eff6ff',
      completed: '#f0fdf4', cancelled: '#fef2f2',
    };
    return m[this.currentStatus] ?? '#eff6ff';
  }

  get statusIcon(): string {
    const m: Record<string, string> = {
      pending: 'clock', confirmed: 'circle-check',
      completed: 'flag-check', cancelled: 'x-circle',
    };
    return m[this.currentStatus] ?? 'calendar-event';
  }

  get statusLabel(): string {
    const m: Record<string, string> = {
      pending: 'În așteptare', confirmed: 'Confirmat',
      completed: 'Finalizat', cancelled: 'Anulat',
    };
    return m[this.currentStatus] ?? this.currentStatus;
  }

  updateStatus(status: string): void {
    this.apiService.patch<any>(`/appointments/${this.data.id}`, { status }).subscribe({
      next: () => {
        this.saved = true;
        this.currentStatus = status;
        setTimeout(() => {
          this.dialogRef.close({ updated: true, id: this.data.id, status });
        }, 900);
      },
      error: () => {},
    });
  }
}

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { ApiService } from '../../services/api';

@Component({
  selector: 'app-assign-patient-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, ReactiveFormsModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title>Atribuie pacient la doctor</h2>
    <mat-dialog-content>
      <form [formGroup]="form" class="d-flex flex-column gap-12 p-t-8">
        <mat-form-field appearance="outline" class="w-100">
          <mat-label>Doctor</mat-label>
          <mat-select formControlName="doctor_id">
            <mat-option *ngFor="let d of doctors" [value]="d.id">
              {{ (d.first_name || d.last_name) ? d.first_name + ' ' + d.last_name : d.email }} — {{ d.specialization }}
            </mat-option>
          </mat-select>
          <mat-error *ngIf="form.get('doctor_id')?.hasError('required')">Selectează un doctor</mat-error>
        </mat-form-field>

        <mat-form-field appearance="outline" class="w-100">
          <mat-label>Pacient</mat-label>
          <mat-select formControlName="patient_id">
            <mat-option *ngFor="let p of patients" [value]="p.id">
              {{ (p.first_name || p.last_name) ? p.first_name + ' ' + p.last_name : p.email }}
            </mat-option>
          </mat-select>
          <mat-error *ngIf="form.get('patient_id')?.hasError('required')">Selectează un pacient</mat-error>
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Anulează</button>
      <button mat-flat-button color="primary" [disabled]="form.invalid" (click)="submit()">Atribuie</button>
    </mat-dialog-actions>
  `,
})
export class AssignPatientDialogComponent implements OnInit {
  form: FormGroup;
  doctors: any[] = [];
  patients: any[] = [];

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<AssignPatientDialogComponent>,
    private apiService: ApiService,
  ) {
    this.form = this.fb.group({
      doctor_id: ['', Validators.required],
      patient_id: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.apiService.get<any[]>('/doctors/').subscribe({
      next: (data) => { this.doctors = data; },
      error: () => {}
    });

    this.apiService.get<any[]>('/patients/').subscribe({
      next: (data) => { this.patients = data; },
      error: () => {}
    });
  }

  submit(): void {
    if (this.form.valid) {
      this.dialogRef.close(this.form.value);
    }
  }
}
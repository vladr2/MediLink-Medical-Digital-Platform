import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';

@Component({
  selector: 'app-create-user-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, ReactiveFormsModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title>Adaugă utilizator nou</h2>
<mat-dialog-content style="min-width: 450px; padding-top: 8px;">
  <form [formGroup]="form">
    <mat-form-field appearance="outline" class="w-100 m-b-8">
      <mat-label>Prenume</mat-label>
      <input matInput formControlName="first_name" placeholder="Ion" />
      <mat-error *ngIf="form.get('first_name')?.hasError('required')">Prenumele este obligatoriu</mat-error>
    </mat-form-field>

    <mat-form-field appearance="outline" class="w-100 m-b-8">
      <mat-label>Nume</mat-label>
      <input matInput formControlName="last_name" placeholder="Popescu" />
      <mat-error *ngIf="form.get('last_name')?.hasError('required')">Numele este obligatoriu</mat-error>
    </mat-form-field>

    <mat-form-field appearance="outline" class="w-100 m-b-8">
      <mat-label>Email</mat-label>
      <input matInput formControlName="email" placeholder="email@exemplu.com" />
      <mat-error *ngIf="form.get('email')?.hasError('required')">Email obligatoriu</mat-error>
      <mat-error *ngIf="form.get('email')?.hasError('email')">Email invalid</mat-error>
    </mat-form-field>

    <mat-form-field appearance="outline" class="w-100 m-b-8">
      <mat-label>Parolă</mat-label>
      <input matInput type="password" formControlName="password" placeholder="••••••••" />
      <mat-error *ngIf="form.get('password')?.hasError('required')">Parola obligatorie</mat-error>
    </mat-form-field>

    <mat-form-field appearance="outline" class="w-100 m-b-8">
      <mat-label>Rol</mat-label>
      <mat-select formControlName="role">
        <mat-option value="patient">Pacient</mat-option>
        <mat-option value="doctor">Doctor</mat-option>
        <mat-option value="assistant">Asistent</mat-option>
        <mat-option value="admin">Admin</mat-option>
      </mat-select>
    </mat-form-field>

    <ng-container *ngIf="form.get('role')?.value === 'doctor'">
      <mat-form-field appearance="outline" class="w-100 m-b-8">
        <mat-label>Specializare</mat-label>
        <input matInput formControlName="specialization" placeholder="Ex: cardiologie" />
      </mat-form-field>

      <mat-form-field appearance="outline" class="w-100 m-b-8">
        <mat-label>Număr licență</mat-label>
        <input matInput formControlName="license_number" placeholder="Ex: MED-002" />
      </mat-form-field>

      <mat-form-field appearance="outline" class="w-100 m-b-8">
        <mat-label>Departament</mat-label>
        <input matInput formControlName="department" placeholder="Ex: Cardiologie" />
      </mat-form-field>
    </ng-container>
  </form>
</mat-dialog-content>
<mat-dialog-actions align="end">
  <button mat-button mat-dialog-close>Anulează</button>
  <button mat-flat-button color="primary" [disabled]="form.invalid" (click)="submit()">Creează</button>
</mat-dialog-actions>
  `,
})
export class CreateUserDialogComponent {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private dialogRef: MatDialogRef<CreateUserDialogComponent>,
  ) {
    this.form = this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required], 
      email: ['', [Validators.required, Validators.email]],
      password: ['', Validators.required],
      role: ['patient', Validators.required],
      specialization: [''],
      license_number: [''],
      department: [''],
    });
  }

  submit(): void {
    if (this.form.valid) {
      this.dialogRef.close(this.form.value);
    }
  }
}
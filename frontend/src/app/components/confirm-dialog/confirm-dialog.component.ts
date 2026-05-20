import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean; // buton roșu când e o acțiune distructivă
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, MatDialogModule, TablerIconsModule],
  template: `
    <div class="p-24">
      <div class="d-flex align-items-center gap-12 m-b-16">
        <div [class]="data.danger ? 'bg-light-error rounded p-10' : 'bg-light-warning rounded p-10'">
          <i-tabler [name]="data.danger ? 'alert-triangle' : 'help-circle'"
                    [class]="data.danger ? 'icon-24 text-error' : 'icon-24 text-warning'">
          </i-tabler>
        </div>
        <h2 mat-dialog-title class="m-0 f-w-600" style="font-size:18px">{{ data.title }}</h2>
      </div>

      <mat-dialog-content>
        <p class="mat-body-1 text-muted m-0">{{ data.message }}</p>
      </mat-dialog-content>

      <mat-dialog-actions align="end" class="m-t-16 gap-8">
        <button mat-stroked-button (click)="cancel()">
          {{ data.cancelText || 'Anulează' }}
        </button>
        <button mat-flat-button
                [color]="data.danger ? 'warn' : 'primary'"
                (click)="confirm()">
          {{ data.confirmText || 'Confirmă' }}
        </button>
      </mat-dialog-actions>
    </div>
  `,
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData,
  ) {}

  confirm(): void { this.dialogRef.close(true); }
  cancel(): void  { this.dialogRef.close(false); }
}

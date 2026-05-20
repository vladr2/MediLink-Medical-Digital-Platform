import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { MatDialogRef, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';

@Component({
  selector: 'app-audit-log-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, MatDialogModule],
  template: `
    <h2 mat-dialog-title>Audit Log complet</h2>
    <mat-dialog-content style="min-width: 700px; max-height: 600px;">
      <table mat-table [dataSource]="data" class="w-100">
        <ng-container matColumnDef="created_at">
          <th mat-header-cell *matHeaderCellDef>Data</th>
          <td mat-cell *matCellDef="let l">{{ l.created_at | date:'dd.MM.yyyy HH:mm:ss' }}</td>
        </ng-container>
        <ng-container matColumnDef="user_email">
          <th mat-header-cell *matHeaderCellDef>Utilizator</th>
          <td mat-cell *matCellDef="let l">{{ l.user_email || '-' }}</td>
        </ng-container>
        <ng-container matColumnDef="action">
          <th mat-header-cell *matHeaderCellDef>Acțiune</th>
          <td mat-cell *matCellDef="let l">
            <mat-chip color="primary" highlighted>{{ l.action }}</mat-chip>
          </td>
        </ng-container>
        <ng-container matColumnDef="details">
          <th mat-header-cell *matHeaderCellDef>Detalii</th>
          <td mat-cell *matCellDef="let l">{{ l.details || '-' }}</td>
        </ng-container>
        <ng-container matColumnDef="ip_address">
          <th mat-header-cell *matHeaderCellDef>IP</th>
          <td mat-cell *matCellDef="let l">{{ l.ip_address || '-' }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="columns; sticky: true"></tr>
        <tr mat-row *matRowDef="let row; columns: columns;"></tr>
      </table>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Închide</button>
    </mat-dialog-actions>
  `,
})
export class AuditLogDialogComponent {
  columns = ['created_at', 'user_email', 'action', 'details', 'ip_address'];
  constructor(
    @Inject(MAT_DIALOG_DATA) public data: any[],
    private dialogRef: MatDialogRef<AuditLogDialogComponent>,
  ) {}
}
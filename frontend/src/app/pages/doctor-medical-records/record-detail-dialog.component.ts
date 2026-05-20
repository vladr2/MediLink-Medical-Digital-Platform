import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { MatDialogRef, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';

@Component({
  selector: 'app-record-detail-dialog',
  standalone: true,
  imports: [CommonModule, MaterialModule, MatDialogModule, TablerIconsModule],
  template: `
    <div style="width:520px;max-width:95vw;overflow:hidden;border-radius:16px;">

      <!-- ── Colored header ─────────────────────────────────────────────────── -->
      <div [style.background]="gradient"
           style="padding:22px 24px 18px;position:relative;">

        <!-- Close btn -->
        <button mat-icon-button (click)="close()"
                style="position:absolute;top:12px;right:12px;
                       background:rgba(255,255,255,.18);border-radius:8px;
                       width:32px;height:32px;min-width:unset;">
          <i-tabler name="x" style="width:16px;height:16px;color:#fff;"></i-tabler>
        </button>

        <div style="display:flex;align-items:center;gap:14px;">
          <!-- Icon circle -->
          <div style="width:50px;height:50px;border-radius:14px;
                      background:rgba(255,255,255,.2);
                      display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <i-tabler [name]="icon" style="width:24px;height:24px;color:#fff;"></i-tabler>
          </div>
          <div>
            <p style="margin:0;font-size:.7rem;font-weight:600;color:rgba(255,255,255,.75);
                      text-transform:uppercase;letter-spacing:.8px;">Detalii înregistrare</p>
            <p style="margin:3px 0 0;font-size:1.05rem;font-weight:800;color:#fff;">
              {{ typeLabel }}
            </p>
            <p style="margin:3px 0 0;font-size:.78rem;color:rgba(255,255,255,.8);">
              <i-tabler name="calendar" style="width:12px;height:12px;vertical-align:middle;margin-right:3px;"></i-tabler>
              {{ data.created_at | date:'dd MMMM yyyy, HH:mm' }}
            </p>
          </div>
        </div>
      </div>

      <!-- ── Content ────────────────────────────────────────────────────────── -->
      <div style="padding:20px 24px 4px;max-height:60vh;overflow-y:auto;">

        <!-- Diagnostic -->
        <div *ngIf="data.diagnosis" style="margin-bottom:14px;">
          <div style="background:linear-gradient(135deg,#fefce8,#fffbeb);
                      border-left:3px solid #ca8a04;border-radius:8px;padding:12px 14px;">
            <p style="margin:0 0 4px;font-size:.67rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.6px;color:#92400e;display:flex;align-items:center;gap:5px;">
              <i-tabler name="stethoscope" style="width:12px;height:12px;"></i-tabler>
              Diagnostic
            </p>
            <p style="margin:0;font-size:.9rem;color:#78350f;line-height:1.6;">{{ data.diagnosis }}</p>
          </div>
        </div>

        <!-- Tratament -->
        <div *ngIf="data.treatment" style="margin-bottom:14px;">
          <div style="background:linear-gradient(135deg,#f5f3ff,#ede9fe);
                      border-left:3px solid #7c3aed;border-radius:8px;padding:12px 14px;">
            <p style="margin:0 0 4px;font-size:.67rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.6px;color:#4c1d95;display:flex;align-items:center;gap:5px;">
              <i-tabler name="pill" style="width:12px;height:12px;"></i-tabler>
              Tratament
            </p>
            <p style="margin:0;font-size:.9rem;color:#4c1d95;line-height:1.6;">{{ data.treatment }}</p>
          </div>
        </div>

        <!-- Rezultat analiză -->
        <div *ngIf="data.analysis_result" style="margin-bottom:14px;">
          <div style="background:linear-gradient(135deg,#f0fdfa,#ecfeff);
                      border-left:3px solid #0d9488;border-radius:8px;padding:12px 14px;">
            <p style="margin:0 0 4px;font-size:.67rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.6px;color:#134e4a;display:flex;align-items:center;gap:5px;">
              <i-tabler name="microscope" style="width:12px;height:12px;"></i-tabler>
              Rezultat analiză / investigație
            </p>
            <p style="margin:0;font-size:.9rem;color:#134e4a;line-height:1.6;">{{ data.analysis_result }}</p>
          </div>
        </div>

        <!-- Note medic -->
        <div *ngIf="data.notes_encrypted" style="margin-bottom:14px;">
          <div style="background:#f8fafc;border:1px solid #e2e8f0;
                      border-radius:8px;padding:12px 14px;">
            <p style="margin:0 0 4px;font-size:.67rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.6px;color:#475569;display:flex;align-items:center;gap:5px;">
              <i-tabler name="notes" style="width:12px;height:12px;"></i-tabler>
              Note medic
            </p>
            <p style="margin:0;font-size:.9rem;color:#374151;line-height:1.6;">{{ data.notes_encrypted }}</p>
          </div>
        </div>

        <!-- Date suplimentare -->
        <div *ngIf="data.data_encrypted" style="margin-bottom:14px;">
          <div style="background:#f8fafc;border:1px dashed #cbd5e1;
                      border-radius:8px;padding:12px 14px;">
            <p style="margin:0 0 4px;font-size:.67rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.6px;color:#64748b;display:flex;align-items:center;gap:5px;">
              <i-tabler name="database" style="width:12px;height:12px;"></i-tabler>
              Date suplimentare
            </p>
            <p style="margin:0;font-size:.9rem;color:#475569;line-height:1.6;">{{ data.data_encrypted }}</p>
          </div>
        </div>

        <!-- Fallback dacă nu are niciun câmp completat -->
        <div *ngIf="!data.diagnosis && !data.treatment && !data.analysis_result && !data.notes_encrypted && !data.data_encrypted"
             style="text-align:center;padding:32px 16px;color:#94a3b8;">
          <i-tabler name="file-description" style="width:36px;height:36px;display:block;margin:0 auto 8px;opacity:.4;"></i-tabler>
          <p style="margin:0;font-size:.85rem;">Nu există detalii suplimentare pentru această înregistrare.</p>
        </div>
      </div>

      <!-- ── Footer ─────────────────────────────────────────────────────────── -->
      <div style="padding:12px 24px 18px;display:flex;align-items:center;justify-content:space-between;">
        <span style="font-size:.68rem;color:#cbd5e1;font-family:monospace;">
          ID: {{ data.id | slice:0:12 }}…
        </span>
        <button mat-flat-button (click)="close()"
                [style.background]="accentColor"
                style="color:#fff;border-radius:8px;font-size:.82rem;height:36px;">
          Închide
        </button>
      </div>
    </div>
  `,
})
export class RecordDetailDialogComponent {
  constructor(
    @Inject(MAT_DIALOG_DATA) public data: any,
    private dialogRef: MatDialogRef<RecordDetailDialogComponent>,
  ) {}

  get gradient(): string {
    const m: Record<string, string> = {
      consultatie: 'linear-gradient(135deg, #2563eb, #7c3aed)',
      analiza:     'linear-gradient(135deg, #0d9488, #06b6d4)',
      tratament:   'linear-gradient(135deg, #7c3aed, #a855f7)',
      reteta:      'linear-gradient(135deg, #ea580c, #f97316)',
      investigatie:'linear-gradient(135deg, #db2777, #f472b6)',
    };
    return m[this.data.record_type] ?? 'linear-gradient(135deg, #64748b, #94a3b8)';
  }

  get accentColor(): string {
    const m: Record<string, string> = {
      consultatie: '#2563eb', analiza: '#0d9488', tratament: '#7c3aed',
      reteta: '#ea580c', investigatie: '#db2777',
    };
    return m[this.data.record_type] ?? '#64748b';
  }

  get icon(): string {
    const m: Record<string, string> = {
      consultatie: 'stethoscope', analiza: 'test-pipe', tratament: 'pill',
      reteta: 'clipboard-text', investigatie: 'scan',
    };
    return m[this.data.record_type] ?? 'report-medical';
  }

  get typeLabel(): string {
    const m: Record<string, string> = {
      consultatie: 'Consultație', analiza: 'Analiză', tratament: 'Tratament',
      reteta: 'Rețetă', investigatie: 'Investigație',
    };
    return m[this.data.record_type] ?? (this.data.record_type || 'Înregistrare');
  }

  close(): void { this.dialogRef.close(); }
}

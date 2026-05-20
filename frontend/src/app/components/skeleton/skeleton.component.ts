import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Skeleton loader reutilizabil.
 * Folosire: <app-skeleton [rows]="3" [card]="true"></app-skeleton>
 */
@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div [class]="card ? 'skeleton-card' : ''">
      <div *ngIf="title" class="skeleton-line skeleton-title m-b-16"></div>
      <div *ngFor="let i of rowArray" class="skeleton-line" [style.width]="getWidth(i)"></div>
    </div>
  `,
  styles: [`
    .skeleton-card {
      background: white;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }
    .skeleton-line {
      height: 14px;
      background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
      background-size: 200% 100%;
      border-radius: 6px;
      margin-bottom: 12px;
      animation: shimmer 1.5s infinite;
    }
    .skeleton-title {
      height: 20px;
      width: 40% !important;
    }
    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `]
})
export class SkeletonComponent {
  @Input() rows = 3;
  @Input() card = true;
  @Input() title = true;

  get rowArray(): number[] {
    return Array.from({ length: this.rows }, (_, i) => i);
  }

  getWidth(index: number): string {
    const widths = ['100%', '85%', '70%', '90%', '60%'];
    return widths[index % widths.length];
  }
}

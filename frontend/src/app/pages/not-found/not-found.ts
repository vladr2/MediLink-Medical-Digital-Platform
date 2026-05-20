import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule],
  template: `
    <div class="not-found-wrapper">
      <div class="not-found-card">
        <div class="icon-wrap">
          <i-tabler name="map-search" class="icon-80 text-primary"></i-tabler>
        </div>
        <h1 class="mat-headline-4 f-w-700 m-0">404</h1>
        <h2 class="mat-subtitle-1 f-w-600 m-t-8 m-b-4">Pagina nu a fost găsită</h2>
        <p class="mat-body-1 text-muted m-b-24">
          Pagina pe care o cauți nu există sau a fost mutată.
        </p>
        <button mat-flat-button color="primary" (click)="goHome()">
          <i-tabler name="home" class="m-r-8"></i-tabler>
          Înapoi la dashboard
        </button>
      </div>
    </div>
  `,
  styles: [`
    .not-found-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 80vh;
      padding: 24px;
    }
    .not-found-card {
      text-align: center;
      max-width: 400px;
    }
    .icon-wrap {
      background: #e3f2fd;
      border-radius: 50%;
      width: 120px;
      height: 120px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 24px;
    }
    h1 {
      font-size: 72px !important;
      color: #1976d2;
      line-height: 1;
    }
  `]
})
export class NotFoundComponent {
  constructor(private router: Router) {}
  goHome(): void {
    this.router.navigate(['/dashboard']);
  }
}

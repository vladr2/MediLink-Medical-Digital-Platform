import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-branding',
  imports: [RouterModule],
  template: `
    <a [routerLink]="['/dashboard']" class="d-flex align-items-center gap-8 text-decoration-none p-x-8">
      <span style="font-size: 24px; font-weight: 700; color: var(--mat-sys-primary);">🏥 MediLink</span>
    </a>
  `,
})
export class BrandingComponent {}
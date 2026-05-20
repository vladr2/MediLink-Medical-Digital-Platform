import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly KEY = 'medilink_theme';
  isDark$ = new BehaviorSubject<boolean>(false);

  constructor() {
    const dark = this.loadInitial();
    this.isDark$.next(dark);
    this.applyToDOM(dark);
  }

  private loadInitial(): boolean {
    try {
      const saved = localStorage.getItem(this.KEY);
      if (saved) return saved === 'dark';
      return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
    } catch { return false; }
  }

  get isDark(): boolean { return this.isDark$.value; }

  toggle(): void { this.set(!this.isDark); }

  set(dark: boolean): void {
    this.isDark$.next(dark);
    localStorage.setItem(this.KEY, dark ? 'dark' : 'light');
    this.applyToDOM(dark);
  }

  /** Sets data-theme on <body> for Material overlay components (menus, dialogs, selects). */
  private applyToDOM(dark: boolean): void {
    document.body.setAttribute('data-theme', dark ? 'dark' : 'light');
  }
}

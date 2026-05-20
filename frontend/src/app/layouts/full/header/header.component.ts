import {
  Component,
  Output,
  EventEmitter,
  Input,
  ViewEncapsulation,
  OnInit,
  OnDestroy,
  HostListener,
} from '@angular/core';
import { TablerIconsModule } from 'angular-tabler-icons';
import { MaterialModule } from 'src/app/material.module';
import { Router, RouterModule, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { CommonModule } from '@angular/common';
import { NgScrollbarModule } from 'ngx-scrollbar';
import { MatBadgeModule } from '@angular/material/badge';
import { AuthService, User } from 'src/app/services/auth';
import { ApiService } from 'src/app/services/api';
import { WebSocketService, AppNotification } from 'src/app/services/websocket.service';
import { ThemeService } from 'src/app/services/theme';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter } from 'rxjs/operators';

@Component({
  selector: 'app-header',
  imports: [
    RouterModule,
    NgScrollbarModule,
    TablerIconsModule,
    MaterialModule,
    MatBadgeModule,
    CommonModule,
  ],
  templateUrl: './header.component.html',
  encapsulation: ViewEncapsulation.None,
})
export class HeaderComponent implements OnInit, OnDestroy {
  @Input() showToggle = true;
  @Input() toggleChecked = false;
  @Output() toggleMobileNav = new EventEmitter<void>();

  currentUser: User | null = null;
  notifications: AppNotification[] = [];
  unreadCount = 0;
  loadingNotifications = false;
  navigating = false;

  // ── Global search ──────────────────────────────────────────────────────────
  searchQuery = '';
  searchResults: { doctors: any[], patients: any[], appointments: any[] } | null = null;
  showSearchDropdown = false;
  loadingSearch = false;
  private searchSubject = new Subject<string>();
  // ──────────────────────────────────────────────────────────────────────────

  private subs = new Subscription();

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    public wsService: WebSocketService,
    private router: Router,
    public themeService: ThemeService,
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
      if (user) {
        this.wsService.connect();
        this.loadNotifications();
      }
    });

    this.subs.add(
      this.wsService.unreadCount$.subscribe(count => {
        this.unreadCount = count;
      })
    );

    // Când vine o notificare nouă, reîncarcă lista
    this.subs.add(
      this.wsService.newNotification$.subscribe(() => {
        this.loadNotifications();
      })
    );

    // ── Global search debounce ─────────────────────────────────────────────
    this.subs.add(
      this.searchSubject.pipe(
        debounceTime(350),
        distinctUntilChanged(),
      ).subscribe(q => {
        if (q.trim().length < 2) {
          this.searchResults = null;
          this.showSearchDropdown = false;
          return;
        }
        this.loadingSearch = true;
        this.apiService.get<any>(`/search/?q=${encodeURIComponent(q)}`).subscribe({
          next: (res) => {
            this.searchResults = res;
            this.showSearchDropdown = true;
            this.loadingSearch = false;
          },
          error: () => { this.loadingSearch = false; }
        });
      })
    );

    // Progress bar la navigare
    this.subs.add(
      this.router.events.subscribe(event => {
        if (event instanceof NavigationStart)  this.navigating = true;
        if (event instanceof NavigationEnd ||
            event instanceof NavigationCancel ||
            event instanceof NavigationError)  this.navigating = false;
      })
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  loadNotifications(): void {
    this.loadingNotifications = true;
    this.apiService.get<AppNotification[]>('/notifications/').subscribe({
      next: (data) => {
        this.notifications = data;
        this.unreadCount = data.filter(n => !n.read).length;
        this.loadingNotifications = false;
      },
      error: () => { this.loadingNotifications = false; }
    });
  }

  markAsRead(notif: AppNotification): void {
    if (notif.read) return;
    this.apiService.patch(`/notifications/${notif.id}/read`, {}).subscribe({
      next: () => {
        notif.read = true;
        this.unreadCount = this.notifications.filter(n => !n.read).length;
        this.wsService.unreadCount$.next(this.unreadCount);
      },
      error: () => {}
    });
  }

  markAllAsRead(): void {
    this.apiService.patch('/notifications/read-all', {}).subscribe({
      next: () => {
        this.notifications.forEach(n => n.read = true);
        this.unreadCount = 0;
        this.wsService.unreadCount$.next(0);
      },
      error: () => {}
    });
  }

  // ── Global search methods ──────────────────────────────────────────────────
  onSearchInput(value: string): void {
    this.searchQuery = value;
    this.searchSubject.next(value);
  }

  closeSearch(): void {
    this.showSearchDropdown = false;
    this.searchQuery = '';
    this.searchResults = null;
    // Resetează Subject-ul ca distinctUntilChanged să permită re-căutarea aceluiași termen
    this.searchSubject.next('');
  }

  navigateToResult(type: string, item: any): void {
    this.closeSearch();
    if (type === 'doctor') {
      this.router.navigate(['/dashboard/doctor', item.user_id]);
    } else if (type === 'patient') {
      const role = this.currentUser?.role;
      if (role === 'doctor') {
        this.router.navigate(['/dashboard/doctor-patients']);
      } else {
        // admin, assistant → pagina cu toți pacienții
        this.router.navigate(['/dashboard/assistant-patients']);
      }
    } else if (type === 'appointment') {
      this.router.navigate(['/dashboard/appointments']);
    }
  }

  get hasSearchResults(): boolean {
    if (!this.searchResults) return false;
    return (
      (this.searchResults.doctors?.length ?? 0) +
      (this.searchResults.patients?.length ?? 0) +
      (this.searchResults.appointments?.length ?? 0)
    ) > 0;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    const target = event.target as HTMLElement;
    if (!target.closest('.ml-search-container')) {
      this.showSearchDropdown = false;
    }
  }
  // ──────────────────────────────────────────────────────────────────────────

  logout(): void {
    this.wsService.disconnect();
    this.authService.logout();
  }

  getInitials(): string {
    if (!this.currentUser) return '?';
    const first = this.currentUser.first_name?.trim();
    const last  = this.currentUser.last_name?.trim();
    if (first && last) return (first[0] + last[0]).toUpperCase();
    if (first)         return first.slice(0, 2).toUpperCase();
    if (last)          return last.slice(0, 2).toUpperCase();
    return this.currentUser.email?.slice(0, 2).toUpperCase() ?? '?';
  }

  getRoleColor(): string {
    const colors: Record<string, string> = {
      admin:     '#7b1fa2',
      doctor:    '#1976d2',
      assistant: '#00796b',
      patient:   '#388e3c',
    };
    return colors[this.currentUser?.role ?? ''] ?? '#1976d2';
  }

  getNotificationIcon(type: string): string {
    const icons: Record<string, string> = {
      appointment: 'calendar',
      warning:     'alert-triangle',
      info:        'info-circle',
    };
    return icons[type] ?? 'bell';
  }

  getTimeAgo(dateStr: string): string {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1)   return 'acum';
    if (mins < 60)  return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)   return `${hrs}h`;
    return `${Math.floor(hrs / 24)}z`;
  }
}

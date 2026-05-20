import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { Subscription } from 'rxjs';
import { MatSidenav, MatSidenavContent } from '@angular/material/sidenav';
import { CoreService } from 'src/app/services/core.service';
import { filter } from 'rxjs/operators';
import { NavigationEnd, Router } from '@angular/router';
import { RouterModule } from '@angular/router';
import { MaterialModule } from 'src/app/material.module';
import { NgScrollbarModule } from 'ngx-scrollbar';
import { TablerIconsModule } from 'angular-tabler-icons';
import { HeaderComponent } from './header/header.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { AppNavItemComponent } from './sidebar/nav-item/nav-item.component';
import { navItemsPatient, navItemsDoctor, navItemsAssistant, navItemsAdmin } from './sidebar/sidebar-data';
import { AuthService } from 'src/app/services/auth';
import { BadgeService } from 'src/app/services/badge';
import { ThemeService } from 'src/app/services/theme';
import { NavItem } from './sidebar/nav-item/nav-item';

const MOBILE_VIEW = 'screen and (max-width: 768px)';
const TABLET_VIEW = 'screen and (min-width: 769px) and (max-width: 1024px)';

@Component({
  selector: 'app-full',
  imports: [
    RouterModule,
    AppNavItemComponent,
    MaterialModule,
    SidebarComponent,
    NgScrollbarModule,
    TablerIconsModule,
    HeaderComponent,
  ],
  templateUrl: './full.component.html',
  styleUrls: [],
  encapsulation: ViewEncapsulation.None,
})
export class FullComponent implements OnInit {
  navItems: NavItem[] = navItemsPatient;
  isDark = false;

  @ViewChild('leftsidenav') public sidenav: MatSidenav;
  resView = false;

  @ViewChild('content', { static: true }) content!: MatSidenavContent;
  options = this.settings.getOptions();
  private layoutChangesSubscription = Subscription.EMPTY;
  private isMobileScreen = false;
  private isContentWidthFixed = true;
  private isCollapsedWidthFixed = false;
  private htmlElement!: HTMLHtmlElement;

  get isOver(): boolean {
    return this.isMobileScreen;
  }

  constructor(
    private settings: CoreService,
    private router: Router,
    private breakpointObserver: BreakpointObserver,
    private authService: AuthService,
    private badgeService: BadgeService,
    private themeService: ThemeService,
  ) {
    // Sync dark mode flag with ThemeService
    this.themeService.isDark$.subscribe(d => this.isDark = d);
    this.htmlElement = document.querySelector('html')!;
    this.layoutChangesSubscription = this.breakpointObserver
      .observe([MOBILE_VIEW, TABLET_VIEW])
      .subscribe((state) => {
        this.options.sidenavOpened = true;
        this.isMobileScreen = state.breakpoints[MOBILE_VIEW];
        if (this.options.sidenavCollapsed == false) {
          this.options.sidenavCollapsed = state.breakpoints[TABLET_VIEW];
        }
      });

    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((e) => {
        this.content.scrollTo({ top: 0 });
      });

    this.authService.currentUser$.subscribe(user => {
      if (!user) { this.badgeService.reset(); return; }
      switch (user.role) {
        case 'doctor':    this.navItems = [...navItemsDoctor];    break;
        case 'assistant': this.navItems = [...navItemsAssistant]; break;
        case 'admin':     this.navItems = [...navItemsAdmin];     break;
        default:          this.navItems = [...navItemsPatient];
      }
      // Badge-uri pentru doctor și admin
      if (user.role === 'doctor' || user.role === 'admin') {
        this.badgeService.refresh();
      }
    });

    // Actualizează badge-ul la fiecare navigare
    this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => {
      const user = this.authService.getCurrentUser();
      if (user?.role === 'doctor' || user?.role === 'admin') {
        this.badgeService.refresh();
      }
    });

    // Aplică badge-ul dinamic pe item-ul de programări
    this.badgeService.pending$.subscribe(count => {
      this.navItems = this.navItems.map(item => {
        if (item.route?.includes('appointments')) {
          return {
            ...item,
            chip: count > 0,
            chipContent: count > 0 ? String(count) : '',
            chipClass: 'bg-warning text-white',
          };
        }
        return item;
      });
    });
  }

  ngOnInit(): void {}

  ngOnDestroy() {
    this.layoutChangesSubscription.unsubscribe();
  }

  toggleCollapsed() {
    this.isContentWidthFixed = false;
    this.options.sidenavCollapsed = !this.options.sidenavCollapsed;
    this.resetCollapsedState();
  }

  resetCollapsedState(timer = 400) {
    setTimeout(() => this.settings.setOptions(this.options), timer);
  }

  onSidenavClosedStart() {
    this.isContentWidthFixed = false;
  }

  onSidenavOpenedChange(isOpened: boolean) {
    this.isCollapsedWidthFixed = !this.isOver;
    this.options.sidenavOpened = isOpened;
  }
}
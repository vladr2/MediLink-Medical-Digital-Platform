import { NavItem } from './nav-item/nav-item';

export const navItemsPatient: NavItem[] = [
  { navCap: 'Principal' },
  { displayName: 'Dashboard', iconName: 'solar:atom-line-duotone', route: '/dashboard' },
  { displayName: 'Chat Medical AI', iconName: 'solar:chat-round-line-line-duotone', route: '/dashboard/chat' },
  { divider: true, navCap: 'Dosar Medical' },
  { displayName: 'Fișă Medicală', iconName: 'solar:document-text-line-duotone', route: '/dashboard/medical-records' },
  { displayName: 'Analize', iconName: 'solar:test-tube-line-duotone', route: '/dashboard/analyses' },
  { displayName: 'Tratamente', iconName: 'solar:pill-line-duotone', route: '/dashboard/treatments' },
  { displayName: 'Prescripții', iconName: 'solar:clipboard-text-line-duotone', route: '/dashboard/prescriptions' },
  { displayName: 'Investigații', iconName: 'solar:medical-kit-line-duotone', route: '/dashboard/investigatii' },
  { divider: true, navCap: 'Monitorizare' },
  { displayName: 'Semne Vitale', iconName: 'solar:heart-pulse-line-duotone', route: '/dashboard/vitals' },
  { displayName: 'Statisticile mele', iconName: 'solar:chart-line-duotone', route: '/dashboard/my-stats' },
  { divider: true, navCap: 'Planificare' },
  { displayName: 'Programări', iconName: 'solar:calendar-mark-line-duotone', route: '/dashboard/appointments' },
  { displayName: 'Calendar', iconName: 'solar:calendar-line-duotone', route: '/dashboard/calendar' },
  { divider: true, navCap: 'Comunicare' },
  { displayName: 'Mesaje', iconName: 'solar:chat-dots-line-duotone', route: '/dashboard/messages' },
  { divider: true, navCap: 'Cont' },
  { displayName: 'Profil', iconName: 'solar:user-line-duotone', route: '/dashboard/profile' },
];

export const navItemsDoctor: NavItem[] = [
  { navCap: 'Principal' },
  { displayName: 'Dashboard', iconName: 'solar:atom-line-duotone', route: '/dashboard/doctor-dashboard' },
  { divider: true, navCap: 'Pacienți' },
  { displayName: 'Pacienții mei', iconName: 'solar:users-group-rounded-line-duotone', route: '/dashboard/doctor-patients' },
  { displayName: 'Fișe Medicale', iconName: 'solar:document-text-line-duotone', route: '/dashboard/doctor-medical-records' },
  { divider: true, navCap: 'Monitorizare' },
  { displayName: 'Semne Vitale Pacienți', iconName: 'solar:heart-pulse-line-duotone', route: '/dashboard/doctor-patient-vitals' },
  { displayName: 'Statistici Pacienți',   iconName: 'solar:chart-line-duotone',       route: '/dashboard/doctor-patient-stats' },
  { divider: true, navCap: 'Activitate' },
  { displayName: 'Programările mele', iconName: 'solar:calendar-mark-line-duotone', route: '/dashboard/appointments' },
  { displayName: 'Mesaje', iconName: 'solar:chat-dots-line-duotone', route: '/dashboard/messages' },
  { displayName: 'Calendar', iconName: 'solar:calendar-line-duotone', route: '/dashboard/calendar' },
  { divider: true, navCap: 'Cont' },
  { displayName: 'Profil', iconName: 'solar:user-line-duotone', route: '/dashboard/profile' },
];

export const navItemsAssistant: NavItem[] = [
  { navCap: 'Principal' },
  { displayName: 'Dashboard', iconName: 'solar:atom-line-duotone', route: '/dashboard/assistant-dashboard' },
  { divider: true, navCap: 'Gestionare' },
  { displayName: 'Programări', iconName: 'solar:calendar-mark-line-duotone', route: '/dashboard/appointments' },
  { displayName: 'Pacienți & Atribuire', iconName: 'solar:users-group-rounded-line-duotone', route: '/dashboard/assistant-patients' },
  { displayName: 'Calendar', iconName: 'solar:calendar-line-duotone', route: '/dashboard/calendar' },
  { divider: true, navCap: 'Monitorizare' },
  { displayName: 'Semne Vitale Pacienți', iconName: 'solar:heart-pulse-line-duotone', route: '/dashboard/doctor-patient-vitals' },
  { displayName: 'Statistici Pacienți',   iconName: 'solar:chart-line-duotone',       route: '/dashboard/doctor-patient-stats' },
  { divider: true, navCap: 'Comunicare' },
  { displayName: 'Mesaje', iconName: 'solar:chat-dots-line-duotone', route: '/dashboard/messages' },
  { divider: true, navCap: 'Cont' },
  { displayName: 'Profil', iconName: 'solar:user-line-duotone', route: '/dashboard/profile' },
];

export const navItemsAdmin: NavItem[] = [
  { navCap: 'Principal' },
  { displayName: 'Dashboard', iconName: 'solar:atom-line-duotone', route: '/dashboard/admin-dashboard' },
  { divider: true, navCap: 'Administrare' },
  { displayName: 'Toate programările', iconName: 'solar:calendar-mark-line-duotone', route: '/dashboard/appointments' },
  { displayName: 'Calendar', iconName: 'solar:calendar-line-duotone', route: '/dashboard/calendar' },
  { divider: true, navCap: 'Cont' },
  { displayName: 'Profil', iconName: 'solar:user-line-duotone', route: '/dashboard/profile' },
];

export const navItems = navItemsPatient;
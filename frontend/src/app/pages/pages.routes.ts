import { Routes } from '@angular/router';
import { StarterComponent } from './starter/starter.component';
import { MedicalDashboardComponent } from './medical-dashboard/medical-dashboard';
import { MedicalChatComponent } from './medical-chat/medical-chat';
import { AppointmentsComponent } from './appointments/appointments';
import { MedicalRecordsComponent } from './medical-records/medical-records';
import { AnalysesComponent } from './analyses/analyses';
import { TreatmentsComponent } from './treatments/treatments';
import { DoctorDashboardComponent } from './doctor-dashboard/doctor-dashboard';
import { AssistantDashboardComponent } from './assistant-dashboard/assistant-dashboard';
import { ProfileComponent } from './profile/profile';
import { AdminComponent } from './admin/admin';
import { AdminDashboardComponent } from './admin-dashboard/admin-dashboard';
import { DoctorPatientsComponent } from './doctor-patients/doctor-patients';
import { DoctorMedicalRecordsComponent } from './doctor-medical-records/doctor-medical-records';
import { AssistantPatientsComponent } from './assistant-patients/assistant-patients';
import { CalendarComponent } from './calendar/calendar';
import { DoctorPublicProfileComponent } from './doctor-public-profile/doctor-public-profile';
import { PrescriptionsComponent } from './prescriptions/prescriptions';
import { VideoCallComponent } from './video-call/video-call';
import { OnboardingComponent } from './onboarding/onboarding';
import { InvestigatiiComponent } from './investigatii/investigatii';


export const PagesRoutes: Routes = [
  {
    path: '',
    component: MedicalDashboardComponent,
    data: { title: 'Dashboard Medical' },
  },
  {
    path: 'starter',
    component: StarterComponent,
    data: { title: 'Starter' },
  },
  {
    path: 'chat',
    component: MedicalChatComponent,
    data: { title: 'Chat Medical' },
  },
  {
    path: 'appointments',
    component: AppointmentsComponent,
    data: { title: 'Programări' },
  },
  {
    path: 'medical-records',
    component: MedicalRecordsComponent,
    data: { title: 'Fișă Medicală' },
  },
  {
    path: 'analyses',
    component: AnalysesComponent,
    data: { title: 'Analize' },
  },
  {
    path: 'treatments',
    component: TreatmentsComponent,
    data: { title: 'Tratamente' },
  },
  {
    path: 'doctor-dashboard',
    component: DoctorDashboardComponent,
    data: { title: 'Dashboard Doctor' },
  },
  {
    path: 'assistant-dashboard',
    component: AssistantDashboardComponent,
    data: { title: 'Dashboard Asistent' },
  },
  {
    path: 'profile',
    component: ProfileComponent,
    data: { title: 'Profil' },
  },
  {
    path: 'admin',
    component: AdminComponent,
    data: { title: 'Admin Panel' },
  },
  {
    path: 'admin-dashboard',
    component: AdminDashboardComponent,
    data: { title: 'Dashboard Admin' },
  },
  {
    path: 'doctor-patients',
    component: DoctorPatientsComponent,
    data: { title: 'Pacienții mei' },
  },
  {
    path: 'doctor-medical-records',
    component: DoctorMedicalRecordsComponent,
    data: { title: 'Fișe Medicale' },
  },
  {
    path: 'assistant-patients',
    component: AssistantPatientsComponent,
    data: { title: 'Lista Pacienților' },
  },
  {
    path: 'calendar',
    component: CalendarComponent,
    data: { title: 'Calendar' },
  },
  {
    path: 'doctor/:id',
    component: DoctorPublicProfileComponent,
    data: { title: 'Profil Doctor' },
  },
  {
    path: 'prescriptions',
    component: PrescriptionsComponent,
    data: { title: 'Prescripții' },
  },
  {
    path: 'investigatii',
    component: InvestigatiiComponent,
    data: { title: 'Investigații' },
  },
  {
    path: 'video/:id',
    component: VideoCallComponent,
    data: { title: 'Teleconsultație' },
  },
  {
    path: 'onboarding',
    component: OnboardingComponent,
    data: { title: 'Configurare profil' },
  },
  {
    path: 'vitals',
    loadComponent: () => import('./vitals/vitals').then(m => m.VitalsComponent),
    data: { title: 'Semne Vitale' },
  },
  {
    path: 'messages',
    loadComponent: () => import('./messages/messages').then(m => m.MessagesComponent),
    data: { title: 'Mesaje' },
  },
  {
    path: 'my-stats',
    loadComponent: () => import('./my-stats/my-stats').then(m => m.MyStatsComponent),
    data: { title: 'Statisticile mele' },
  },
  {
    path: 'doctor-patient-vitals',
    loadComponent: () => import('./doctor-patient-vitals/doctor-patient-vitals').then(m => m.DoctorPatientVitalsComponent),
    data: { title: 'Semne Vitale Pacienți' },
  },
  {
    path: 'doctor-patient-stats',
    loadComponent: () => import('./doctor-patient-stats/doctor-patient-stats').then(m => m.DoctorPatientStatsComponent),
    data: { title: 'Statistici Pacienți' },
  },
];
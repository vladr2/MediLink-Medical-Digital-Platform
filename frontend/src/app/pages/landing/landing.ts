import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { AuthService } from '../../services/auth';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule, RouterModule, MaterialModule, TablerIconsModule],
  templateUrl: './landing.html',
})
export class LandingComponent implements OnInit {
  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    // Dacă utilizatorul e deja autentificat, trimite-l direct la dashboard
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/dashboard']);
    }
  }

  features = [
    {
      icon: 'shield-lock',
      color: '#1976d2',
      bg: '#e3f2fd',
      title: 'Securitate medicală',
      desc: 'Criptare AES-128 Fernet pe toate datele sensibile. Audit log complet, rate limiting și conformitate GDPR Art. 20.',
    },
    {
      icon: 'robot',
      color: '#7b1fa2',
      bg: '#f3e5f5',
      title: 'Asistent AI integrat',
      desc: 'Chat medical inteligent powered by Groq LLM. Detectare automată a specializărilor și recomandare doctori din rețea.',
    },
    {
      icon: 'calendar-check',
      color: '#388e3c',
      bg: '#e8f5e9',
      title: 'Gestionare completă',
      desc: 'Programări, fișe medicale, analize, tratamente și calendar vizual pentru pacienți, doctori și asistenți.',
    },
    {
      icon: 'bell',
      color: '#e65100',
      bg: '#fff3e0',
      title: 'Notificări în timp real',
      desc: 'Sistem de notificări WebSocket. Doctorii primesc instant alertă când un pacient solicită o programare.',
    },
  ];

  roles = [
    { icon: 'user-heart',   color: '#388e3c', label: 'Pacient',   desc: 'Programări, fișă medicală, export GDPR, chat AI' },
    { icon: 'stethoscope',  color: '#1976d2', label: 'Doctor',    desc: 'Dashboard grafice, fișe pacienți, calendar' },
    { icon: 'user-cog',     color: '#00796b', label: 'Asistent',  desc: 'Gestionare pacienți, programări, suport' },
    { icon: 'shield-check', color: '#7b1fa2', label: 'Admin',     desc: 'Statistici, utilizatori, audit log complet' },
  ];

  stats = [
    { value: '4',    label: 'Roluri de utilizator' },
    { value: 'AES',  label: 'Criptare date sensibile' },
    { value: 'GDPR', label: 'Conformitate Art. 20' },
    { value: 'AI',   label: 'Asistent medical integrat' },
  ];
}

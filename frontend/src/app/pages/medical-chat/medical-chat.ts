import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MaterialModule } from '../../material.module';
import { ApiService } from '../../services/api';
import { TablerIconsModule } from 'angular-tabler-icons';

interface Message {
  role: 'user' | 'assistant';
  content: string;       // text raw (pentru copiere etc.)
  htmlContent: SafeHtml; // HTML formatat (markdown rendered)
  timestamp: Date;
}

interface SuggestedDoctor {
  user_id: string;
  name: string;
  specialization: string;
  department: string | null;
}

@Component({
  selector: 'app-medical-chat',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule],
  templateUrl: './medical-chat.html',
})
export class MedicalChatComponent implements OnInit, AfterViewChecked {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  messages: Message[] = [];
  newMessage = '';
  loading = false;
  conversationId: string | null = null;
  suggestedDoctor: SuggestedDoctor | null = null;
  private shouldScroll = false;

  // Quick suggestions afișate când nu există mesaje utilizator
  quickSuggestions: string[] = [];
  loadingQuestions = false;

  constructor(
    private apiService: ApiService,
    private router: Router,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    this.pushAssistantMessage(
      'Bună ziua! Sunt **asistentul medical MediLink**, alimentat de Groq AI.\n\n' +
      'Vă pot ajuta cu:\n' +
      '- Explicarea termenilor și informațiilor medicale\n' +
      '- Orientarea spre specialistul potrivit\n' +
      '- Întrebări despre istoricul dvs. medical\n\n' +
      'Cum vă pot ajuta astăzi?'
    );
    this.loadSuggestedQuestions();
  }

  loadSuggestedQuestions(): void {
    this.loadingQuestions = true;
    this.apiService.get<{ questions: string[] }>('/chat/suggested-questions').subscribe({
      next: (res) => {
        this.quickSuggestions = res.questions ?? [];
        this.loadingQuestions = false;
      },
      error: () => {
        this.quickSuggestions = [
          'Ce analize am înregistrate recent?',
          'Explică-mi diagnosticul cel mai recent',
          'Vreau să programez o consultație',
          'Am dureri de cap frecvente, ce specialist să consult?',
          'Ce tratamente am urmat?',
        ];
        this.loadingQuestions = false;
      },
    });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  // ── Helpers mesaje ─────────────────────────────────────────────────────────

  private pushAssistantMessage(content: string): void {
    this.messages.push({
      role: 'assistant',
      content,
      htmlContent: this.toHtml(content),
      timestamp: new Date(),
    });
    this.shouldScroll = true;
  }

  get showQuickSuggestions(): boolean {
    return this.messages.filter(m => m.role === 'user').length === 0 && !this.loading;
  }

  // ── Trimitere mesaj ────────────────────────────────────────────────────────

  sendMessage(text?: string): void {
    const userMessage = (text ?? this.newMessage).trim();
    if (!userMessage || this.loading) return;

    this.messages.push({
      role: 'user',
      content: userMessage,
      htmlContent: this.sanitizer.bypassSecurityTrustHtml(
        this.escapeHtml(userMessage).replace(/\n/g, '<br>')
      ),
      timestamp: new Date(),
    });

    this.newMessage = '';
    this.loading = true;
    this.suggestedDoctor = null;
    this.shouldScroll = true;

    const body: any = { message: userMessage };
    if (this.conversationId) body.conversation_id = this.conversationId;

    this.apiService.post<any>('/chat/', body).subscribe({
      next: (response) => {
        this.conversationId = response.conversation_id;
        this.pushAssistantMessage(response.message);
        if (response.suggested_doctor) {
          this.suggestedDoctor = response.suggested_doctor;
        }
        this.loading = false;
      },
      error: () => {
        this.pushAssistantMessage('A apărut o eroare de comunicare. Vă rugăm să încercați din nou.');
        this.loading = false;
      },
    });
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  clearConversation(): void {
    this.messages = [];
    this.conversationId = null;
    this.suggestedDoctor = null;
    this.newMessage = '';
    this.pushAssistantMessage(
      'Conversație nouă pornită. Cum vă pot ajuta?'
    );
  }

  // ── Doctor recommendation ──────────────────────────────────────────────────

  viewDoctorProfile(): void {
    if (this.suggestedDoctor?.user_id) {
      this.router.navigate([`/dashboard/doctor/${this.suggestedDoctor.user_id}`]);
    }
  }

  bookAppointment(): void {
    this.router.navigate(['/dashboard/appointments']);
  }

  getDoctorInitials(name: string): string {
    const parts = name.trim().split(' ').filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }

  // ── Formatare timp ─────────────────────────────────────────────────────────

  formatTime(date: Date): string {
    return date.toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' });
  }

  // ── Markdown → HTML ────────────────────────────────────────────────────────

  private toHtml(text: string): SafeHtml {
    const lines = text.split('\n');
    const out: string[] = [];
    let inUl = false;
    let inOl = false;

    const closeList = () => {
      if (inUl) { out.push('</ul>'); inUl = false; }
      if (inOl) { out.push('</ol>'); inOl = false; }
    };

    for (const raw of lines) {
      const line = raw.trimEnd();
      const ulMatch = line.match(/^[\s]*[-•*]\s+(.*)/);
      const olMatch = line.match(/^[\s]*\d+[.)]\s+(.*)/);

      if (ulMatch) {
        if (inOl) { out.push('</ol>'); inOl = false; }
        if (!inUl) { out.push('<ul style="margin:6px 0 6px 18px;padding:0">'); inUl = true; }
        out.push(`<li style="margin-bottom:3px">${this.inlineFormat(ulMatch[1])}</li>`);
      } else if (olMatch) {
        if (inUl) { out.push('</ul>'); inUl = false; }
        if (!inOl) { out.push('<ol style="margin:6px 0 6px 18px;padding:0">'); inOl = true; }
        out.push(`<li style="margin-bottom:3px">${this.inlineFormat(olMatch[1])}</li>`);
      } else {
        closeList();
        if (line.trim() === '') {
          out.push('<div style="height:5px"></div>');
        } else {
          out.push(`<p style="margin:0 0 5px;line-height:1.55">${this.inlineFormat(line)}</p>`);
        }
      }
    }
    closeList();

    return this.sanitizer.bypassSecurityTrustHtml(out.join(''));
  }

  private inlineFormat(text: string): string {
    return this.escapeHtml(text)
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,.07);padding:1px 5px;border-radius:3px;font-size:.88em">$1</code>');
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  // ── Scroll ─────────────────────────────────────────────────────────────────

  private scrollToBottom(): void {
    try {
      const el = this.messagesContainer?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    } catch {}
  }
}

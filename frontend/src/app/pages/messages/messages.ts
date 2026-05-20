import { Component, OnInit, OnDestroy, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { ApiService } from '../../services/api';
import { AuthService, User } from '../../services/auth';
import { WebSocketService } from '../../services/websocket.service';
import { SkeletonComponent } from '../../components/skeleton/skeleton.component';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { Subscription } from 'rxjs';
import { ActivatedRoute } from '@angular/router';

interface Conversation {
  partner_id: string;
  partner_name: string;
  partner_role: string;
  last_message: string;
  last_message_at: string;
  unread_count: number;
}

interface Message {
  id: string;
  sender_id: string;
  receiver_id: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

@Component({
  selector: 'app-messages',
  standalone: true,
  imports: [CommonModule, FormsModule, MaterialModule, TablerIconsModule, SkeletonComponent],
  templateUrl: './messages.html',
})
export class MessagesComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChild('messagesEnd') messagesEnd!: ElementRef;

  conversations: Conversation[] = [];
  messages: Message[] = [];
  selectedConv: Conversation | null = null;
  currentUser: User | null = null;

  loadingConvs  = true;
  loadingMsgs   = false;
  sending       = false;
  newMessage    = '';

  // ── Conversație nouă ────────────────────────────────────────────────────
  showContacts    = false;
  contacts: any[] = [];
  loadingContacts = false;
  contactSearch   = '';

  private subs = new Subscription();
  private pollTimer: any = null;
  private shouldScroll = false;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private wsService: WebSocketService,
    private sanitizer: DomSanitizer,
    private route: ActivatedRoute,
  ) {}

  ngOnInit(): void {
    this.subs.add(
      this.authService.currentUser$.subscribe(u => { this.currentUser = u; })
    );
    this.loadConversations();

    // Ascultă mesaje noi prin WebSocket
    this.subs.add(
      this.wsService.newMessage$.subscribe(ev => {
        // Refresh conversații
        this.loadConversations(false);
        // Dacă conversația activă e cu expeditorul, reîncarcă mesajele
        if (this.selectedConv?.partner_id === ev.from_id) {
          this.loadMessages(this.selectedConv, false);
          this.markRead(this.selectedConv.partner_id);
        }
      })
    );

    // Query param ?partner=UUID (opțional, pentru deschidere directă)
    this.subs.add(
      this.route.queryParams.subscribe(params => {
        if (params['partner']) {
          // Așteptăm să se încarce conversațiile, apoi selectăm
          setTimeout(() => {
            const conv = this.conversations.find(c => c.partner_id === params['partner']);
            if (conv) this.selectConversation(conv);
          }, 600);
        }
      })
    );
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    clearInterval(this.pollTimer);
  }

  loadConversations(showLoading = true): void {
    if (showLoading) this.loadingConvs = true;
    this.apiService.get<Conversation[]>('/messages/conversations').subscribe({
      next: (data) => {
        this.conversations = data;
        this.loadingConvs = false;
        // Actualizează unread_count pe conversația activă
        if (this.selectedConv) {
          const updated = data.find(c => c.partner_id === this.selectedConv!.partner_id);
          if (updated) this.selectedConv = updated;
        }
      },
      error: () => { this.loadingConvs = false; },
    });
  }

  selectConversation(conv: Conversation): void {
    this.selectedConv = conv;
    this.loadMessages(conv);
    this.markRead(conv.partner_id);
    // Polling la fiecare 8s când o conversație e deschisă
    clearInterval(this.pollTimer);
    this.pollTimer = setInterval(() => {
      if (this.selectedConv) this.loadMessages(this.selectedConv, false);
    }, 8000);
  }

  loadMessages(conv: Conversation, showLoading = true): void {
    if (showLoading) this.loadingMsgs = true;
    this.apiService.get<Message[]>(`/messages/conversation/${conv.partner_id}`).subscribe({
      next: (data) => {
        const wasAtBottom = this.isAtBottom();
        this.messages = data;
        this.loadingMsgs = false;
        if (wasAtBottom || showLoading) this.shouldScroll = true;
      },
      error: () => { this.loadingMsgs = false; },
    });
  }

  markRead(partnerId: string): void {
    this.apiService.post(`/messages/read/${partnerId}`, {}).subscribe({
      next: () => {
        const conv = this.conversations.find(c => c.partner_id === partnerId);
        if (conv) conv.unread_count = 0;
      },
      error: () => {},
    });
  }

  sendMessage(): void {
    const content = this.newMessage.trim();
    if (!content || !this.selectedConv || this.sending) return;
    this.sending = true;
    this.apiService.post<Message>('/messages/', {
      receiver_id: this.selectedConv.partner_id,
      content,
    }).subscribe({
      next: (msg) => {
        this.messages.push(msg);
        this.newMessage = '';
        this.sending = false;
        this.shouldScroll = true;
        this.loadConversations(false);
      },
      error: () => { this.sending = false; },
    });
  }

  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  renderMarkdown(text: string): SafeHtml {
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // ```code block```
      .replace(/```([\s\S]*?)```/g, '<pre style="background:#f1f5f9;border-radius:6px;padding:8px 12px;font-size:.82rem;overflow-x:auto;margin:4px 0;">$1</pre>')
      // `inline code`
      .replace(/`([^`]+)`/g, '<code style="background:#f1f5f9;border-radius:3px;padding:1px 5px;font-size:.85em;">$1</code>')
      // **bold**
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      // *italic*
      .replace(/\*([^*]+)\*/g, '<em>$1</em>')
      // newlines → <br>
      .replace(/\n/g, '<br>');
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  formatTime(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000 && d.getDate() === now.getDate()) {
      return d.toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString('ro-RO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  formatConvTime(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    if (d.getDate() === now.getDate() && d.getMonth() === now.getMonth()) {
      return d.toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString('ro-RO', { day: '2-digit', month: 'short' });
  }

  private scrollToBottom(): void {
    try {
      this.messagesEnd?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
    } catch {}
  }

  private isAtBottom(): boolean {
    const el = this.messagesEnd?.nativeElement?.parentElement;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }

  get totalUnread(): number {
    return this.conversations.reduce((s, c) => s + c.unread_count, 0);
  }

  // ── Conversație nouă ────────────────────────────────────────────────────

  toggleContacts(): void {
    this.showContacts = !this.showContacts;
    if (this.showContacts && this.contacts.length === 0) {
      this.loadContacts();
    }
  }

  loadContacts(): void {
    this.loadingContacts = true;
    this.apiService.get<any[]>('/messages/contacts').subscribe({
      next: (data) => { this.contacts = data; this.loadingContacts = false; },
      error: () => { this.loadingContacts = false; },
    });
  }

  get filteredContacts(): any[] {
    const q = this.contactSearch.trim().toLowerCase();
    if (!q) return this.contacts;
    return this.contacts.filter(c => {
      const name = `${c.first_name || ''} ${c.last_name || ''} ${c.email || ''}`.toLowerCase();
      return name.includes(q);
    });
  }

  contactName(c: any): string {
    const n = `${c.first_name || ''} ${c.last_name || ''}`.trim();
    return n || c.email || '—';
  }

  openConversationWith(contact: any): void {
    const role = this.currentUser?.role;
    // Contactele vin din /messages/contacts cu câmpul `role` explicit
    const partnerId   = contact.user_id;
    const partnerRole = contact.role || (role === 'doctor' ? 'patient' : 'doctor');
    const prefix      = partnerRole === 'doctor' ? 'Dr. ' : '';
    const name        = prefix + this.contactName(contact);

    // Dacă există deja conversația, o selectăm
    const existing = this.conversations.find(c => c.partner_id === partnerId);
    if (existing) {
      this.selectConversation(existing);
    } else {
      // Conversație nouă (fără mesaje încă)
      this.selectedConv = {
        partner_id:      partnerId,
        partner_name:    name,
        partner_role:    partnerRole,
        last_message:    '',
        last_message_at: new Date().toISOString(),
        unread_count:    0,
      };
      this.messages = [];
      this.loadingMsgs = false;
      clearInterval(this.pollTimer);
      this.pollTimer = setInterval(() => {
        if (this.selectedConv) this.loadMessages(this.selectedConv, false);
      }, 8000);
    }

    this.showContacts  = false;
    this.contactSearch = '';
  }
}

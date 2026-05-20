import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { Router } from '@angular/router';

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  type: string;
  read: boolean;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  private socket: WebSocket | null = null;
  private reconnectTimer: any = null;
  private reconnectDelay = 3000;
  private maxReconnectDelay = 30000;
  private destroyed = false;

  /** Numărul de notificări necitite */
  unreadCount$ = new BehaviorSubject<number>(0);

  /** Emite când vine o notificare nouă (pentru toast opțional) */
  newNotification$ = new Subject<{ title: string; message: string }>();

  /** Emite când vine un mesaj nou (pentru badge + refresh) */
  newMessage$ = new Subject<{ from_id: string; from_name: string; preview: string; unread_messages: number }>();

  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) return;
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host  = window.location.host;
    const url   = `${proto}://${host}/api/notifications/ws?token=${token}`;

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      this.reconnectDelay = 3000;  // reset backoff
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'init' || data.type === 'new_notification') {
          this.unreadCount$.next(data.unread_count ?? 0);
        }
        if (data.type === 'new_notification') {
          this.newNotification$.next({ title: data.title, message: data.message });
        }
        if (data.type === 'ping') {
          this.socket?.send('ping');
        }
        if (data.type === 'new_message') {
          this.newMessage$.next({
            from_id: data.from_id,
            from_name: data.from_name,
            preview: data.preview,
            unread_messages: data.unread_messages ?? 0,
          });
        }
      } catch {}
    };

    this.socket.onclose = () => {
      if (!this.destroyed) this.scheduleReconnect();
    };

    this.socket.onerror = () => {
      this.socket?.close();
    };
  }

  disconnect(): void {
    this.destroyed = true;
    clearTimeout(this.reconnectTimer);
    this.socket?.close();
    this.socket = null;
    this.unreadCount$.next(0);
  }

  /** Apelat după logout + reconectare cu token nou */
  reconnect(): void {
    this.destroyed = false;
    this.socket?.close();
    this.socket = null;
    clearTimeout(this.reconnectTimer);
    this.connect();
  }

  private scheduleReconnect(): void {
    clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}

import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { Clipboard, ClipboardModule } from '@angular/cdk/clipboard';
import { MaterialModule } from '../../material.module';
import { TablerIconsModule } from 'angular-tabler-icons';
import { NotificationService } from '../../services/notification';

const STUN = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

@Component({
  selector: 'app-video-call',
  standalone: true,
  imports: [CommonModule, MaterialModule, TablerIconsModule, ClipboardModule],
  templateUrl: './video-call.html',
})
export class VideoCallComponent implements OnInit, OnDestroy {
  @ViewChild('localVideo',  { static: false }) localVideoRef!: ElementRef<HTMLVideoElement>;
  @ViewChild('remoteVideo', { static: false }) remoteVideoRef!: ElementRef<HTMLVideoElement>;

  appointmentId = '';
  status: 'connecting' | 'waiting' | 'in-call' | 'ended' | 'error' = 'connecting';
  errorMsg = '';

  micOn    = true;
  cameraOn = true;
  callDuration = 0;

  private ws!: WebSocket;
  private pc!: RTCPeerConnection;
  private localStream!: MediaStream;
  private callTimer: any;
  private isCaller = false;   // primul conectat face offer

  callUrl = '';
  linkCopied = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private notification: NotificationService,
    private clipboard: Clipboard,
  ) {}

  ngOnInit(): void {
    this.appointmentId = this.route.snapshot.paramMap.get('id') || '';
    this.callUrl = window.location.href;
    this.startCall();
  }

  ngOnDestroy(): void {
    this.cleanup();
  }

  async startCall(): Promise<void> {
    try {
      // 1. Obține stream local
      this.localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      // Atribuie după ce view-ul e gata
      setTimeout(() => {
        if (this.localVideoRef?.nativeElement) {
          this.localVideoRef.nativeElement.srcObject = this.localStream;
        }
      }, 100);

      // 2. Conectează WebSocket signaling
      const token = localStorage.getItem('access_token') || '';
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const wsUrl = `${proto}://${location.host}/api/video/ws/${this.appointmentId}?token=${token}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen    = () => { this.status = 'waiting'; };
      this.ws.onmessage = (e) => this.handleSignal(JSON.parse(e.data));
      this.ws.onerror   = () => { this.status = 'error'; this.errorMsg = 'Eroare conexiune server.'; };
      this.ws.onclose   = (e) => {
        if (e.code === 4001) { this.status = 'error'; this.errorMsg = 'Autentificare eșuată.'; }
        if (e.code === 4003) { this.status = 'error'; this.errorMsg = 'Nu ești participant la această programare sau programarea nu e confirmată.'; }
      };
    } catch (err: any) {
      this.status = 'error';
      this.errorMsg = err.name === 'NotAllowedError'
        ? 'Accesul la cameră/microfon a fost refuzat. Permite accesul în setările browserului.'
        : 'Nu s-a putut accesa camera sau microfonul.';
    }
  }

  private async handleSignal(msg: any): Promise<void> {
    const { type } = msg;

    if (type === 'peer-joined') {
      // Al doilea conectat primește peer-joined → inițiez offer dacă eu sunt primul
      if (!this.isCaller) {
        this.isCaller = true;
        await this.createPeerConnection();
        const offer = await this.pc.createOffer();
        await this.pc.setLocalDescription(offer);
        this.send({ type: 'offer', sdp: offer.sdp });
      }
    }

    if (type === 'offer') {
      await this.createPeerConnection();
      await this.pc.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: msg.sdp }));
      const answer = await this.pc.createAnswer();
      await this.pc.setLocalDescription(answer);
      this.send({ type: 'answer', sdp: answer.sdp });
    }

    if (type === 'answer') {
      await this.pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: msg.sdp }));
    }

    if (type === 'ice-candidate' && msg.candidate) {
      try { await this.pc.addIceCandidate(new RTCIceCandidate(msg.candidate)); } catch {}
    }

    if (type === 'peer-left') {
      this.status = 'ended';
      this.stopCallTimer();
      if (this.remoteVideoRef?.nativeElement) this.remoteVideoRef.nativeElement.srcObject = null;
      this.notification.info('Celălalt participant a părăsit apelul.');
    }
  }

  private async createPeerConnection(): Promise<void> {
    this.pc = new RTCPeerConnection(STUN);

    this.localStream.getTracks().forEach(t => this.pc.addTrack(t, this.localStream));

    this.pc.onicecandidate = (e) => {
      if (e.candidate) this.send({ type: 'ice-candidate', candidate: e.candidate });
    };

    this.pc.ontrack = (e) => {
      this.status = 'in-call';
      this.startCallTimer();
      setTimeout(() => {
        if (this.remoteVideoRef?.nativeElement) {
          this.remoteVideoRef.nativeElement.srcObject = e.streams[0];
        }
      }, 100);
    };
  }

  toggleMic(): void {
    this.micOn = !this.micOn;
    this.localStream.getAudioTracks().forEach(t => t.enabled = this.micOn);
  }

  toggleCamera(): void {
    this.cameraOn = !this.cameraOn;
    this.localStream.getVideoTracks().forEach(t => t.enabled = this.cameraOn);
  }

  hangUp(): void {
    this.send({ type: 'leave' });
    this.cleanup();
    this.status = 'ended';
  }

  copyLink(): void {
    this.clipboard.copy(this.callUrl);
    this.linkCopied = true;
    setTimeout(() => this.linkCopied = false, 2500);
  }

  goBack(): void {
    this.router.navigate(['/dashboard/appointments']);
  }

  private send(msg: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private startCallTimer(): void {
    this.callTimer = setInterval(() => this.callDuration++, 1000);
  }

  private stopCallTimer(): void {
    clearInterval(this.callTimer);
  }

  get callDurationStr(): string {
    const m = Math.floor(this.callDuration / 60).toString().padStart(2, '0');
    const s = (this.callDuration % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  private cleanup(): void {
    this.stopCallTimer();
    this.localStream?.getTracks().forEach(t => t.stop());
    this.pc?.close();
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.close();
  }
}

import { Component, ChangeDetectorRef, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  sql?: string;
  hasChart?: boolean;
}

@Component({
  selector: 'app-chat-widget',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-widget.html',
  styleUrl: './chat-widget.css'
})
export class ChatWidget implements AfterViewChecked {
  isOpen    = false;
  userQuery = '';
  loading   = false;
  showSql   = false;

  messages: ChatMessage[] = [{
    sender: 'ai',
    text:   'Merhaba! Ben DataPulse AI Asistanım 🤖\n\nE-ticaret verileriniz hakkında sorular sorabilirsiniz. Örneğin:\n• "Geçen ayki satışları göster"\n• "En çok satan 5 ürün"\n• "Kategori bazlı gelir dağılımı"'
  }];

  @ViewChild('chatScroll') private chatScrollRef!: ElementRef;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private cdr: ChangeDetectorRef
  ) {}

  toggleChat() { this.isOpen = !this.isOpen; }

  ngAfterViewChecked() {
    try {
      this.chatScrollRef.nativeElement.scrollTop = this.chatScrollRef.nativeElement.scrollHeight;
    } catch {}
  }

  sendMessage() {
    const q = this.userQuery.trim();
    if (!q || this.loading) return;

    this.messages.push({ sender: 'user', text: q });
    this.userQuery = '';
    this.loading   = true;

    // Try backend proxy first (passes JWT); fall back to direct Python call
    const body = { question: q };

    this.http.post<any>(`${environment.apiUrl}/chat/ask`, body).subscribe({
      next: res => {
        const d = res?.data ?? res;
        this.pushAiMessage(d);
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.messages.push({
          sender: 'ai',
          text:   '⚠️ AI servisine ulaşılamadı.\n\nLütfen şunları kontrol edin:\n1. Backend: `mvn spring-boot:run`\n2. Chatbot: `python main.py`'
        });
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  private pushAiMessage(d: any) {
    const answer   = d?.answer   ?? 'Yanıt alınamadı.';
    const sql      = d?.sql      ?? null;
    const plotData = d?.plotData ?? null;
    this.messages.push({ sender: 'ai', text: answer, sql, hasChart: !!plotData });
  }

  formatText(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\n/g, '<br>')
      .replace(/•/g, '&bull;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }
}

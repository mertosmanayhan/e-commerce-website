import { Component, ChangeDetectorRef, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { AuthService } from '../auth.service';

interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  sql?: string;
}

@Component({
  selector: 'app-ai-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './ai-assistant.html',
  styleUrl: './ai-assistant.css'
})
export class AiAssistant implements AfterViewChecked {
  userQuery = '';
  loading   = false;
  isAdmin   = false;

  messages: ChatMessage[] = [{
    sender: 'ai',
    text: 'Merhaba! Ben DataPulse AI Asistanım 🤖\n\nE-ticaret verileriniz hakkında sorular sorabilirsiniz:\n• "Geçen ayki satışları göster"\n• "En çok satan 5 ürün"\n• "Kategori bazlı gelir dağılımı"\n• "Bekleyen siparişler kaç tane?"'
  }];

  suggestions = [
    'En çok satan 5 ürün nedir?',
    'Bu ayki toplam gelir nedir?',
    'Bekleyen siparişler kaç tane?',
    'Kategori bazlı gelir dağılımı'
  ];

  @ViewChild('chatScroll') private chatScrollRef!: ElementRef;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {
    const user = this.authService.getCurrentUser();
    this.isAdmin = user?.role === 'ADMIN';
  }

  get user() { return this.authService.getCurrentUser(); }

  ngAfterViewChecked() {
    try { this.chatScrollRef.nativeElement.scrollTop = this.chatScrollRef.nativeElement.scrollHeight; } catch {}
  }

  useSuggestion(s: string) {
    this.userQuery = s;
    this.sendMessage();
  }

  sendMessage() {
    const q = this.userQuery.trim();
    if (!q || this.loading) return;
    this.messages.push({ sender: 'user', text: q });
    this.userQuery = '';
    this.loading = true;
    this.cdr.detectChanges();

    this.http.post<any>(`${environment.apiUrl}/chat/ask`, { question: q }).subscribe({
      next: res => {
        const d = res?.data ?? res;
        this.messages.push({ sender: 'ai', text: d?.answer ?? 'Yanıt alınamadı.', sql: d?.sql });
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.http.post<any>('http://localhost:8000/api/chat/ask',
          { message: q, role: this.user?.role ?? 'INDIVIDUAL' }
        ).subscribe({
          next: d => {
            this.messages.push({ sender: 'ai', text: d?.answer ?? 'Yanıt alınamadı.', sql: d?.sql });
            this.loading = false;
            this.cdr.detectChanges();
          },
          error: () => {
            this.messages.push({ sender: 'ai', text: '⚠️ AI servisi şu an ulaşılamıyor.\n\nChatbot\'u başlatmak için:\ncd chatbot-service && python main.py' });
            this.loading = false;
            this.cdr.detectChanges();
          }
        });
      }
    });
  }

  formatText(text: string): string {
    return text.replace(/\n/g, '<br>').replace(/•/g, '&bull;');
  }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
}

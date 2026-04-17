import {
  Component, ChangeDetectorRef, ViewChild, ElementRef,
  AfterViewChecked, OnInit
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../auth.service';
import { environment } from '../../environments/environment';

declare const Plotly: any;

interface ChatMessage {
  sender:       'user' | 'ai';
  text:         string;
  sql?:         string;
  plotData?:    string;   // Plotly JSON string
  loading?:     boolean;
  thinkingText?: string;  // current thinking phase shown while loading
  chartId?:     string;
}

@Component({
  selector: 'app-ai-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './ai-assistant.html',
  styleUrl: './ai-assistant.css'
})
export class AiAssistant implements OnInit, AfterViewChecked {
  userQuery     = '';
  loading       = false;
  isAdmin       = false;
  isCorp        = false;
  isIndividual  = false;
  private shouldScroll  = false;
  private chartCounter  = 0;
  private thinkingTimer: any = null;

  readonly THINKING_PHASES = [
    'Sorgunuz analiz ediliyor...',
    'Kapsam doğrulanıyor...',
    'SQL sorgusu oluşturuluyor...',
    'Veritabanı sorgulanıyor...',
    'Sonuçlar yorumlanıyor...',
    'Grafik hazırlanıyor...',
  ];

  private readonly ROLE_CONFIG: Record<string, { welcome: string; suggestions: string[] }> = {
    ADMIN: {
      welcome:
        'Merhaba Admin! Ben DataPulse AI Asistanım 🤖\n\n' +
        'Tüm platforma tam erişiminiz var. Sorgulayabilecekleriniz:\n' +
        '• "Tüm mağazaların toplam gelirini göster"\n' +
        '• "Platform geneli sipariş durum dağılımı"\n' +
        '• "En çok satan 10 ürün hangileri?"\n' +
        '• "Aylık gelir trendi"\n' +
        '• "Tüm kullanıcı şehir dağılımı"',
      suggestions: [
        'Platform geneli toplam gelir özeti',
        'Tüm mağazaların sipariş durum dağılımı',
        'En çok satan 10 ürün hangileri?',
        'Kategori bazlı platform geliri',
        'Tüm kullanıcı şehir dağılımı',
        'Üyelik tipi dağılımı ve harcamalar',
        'Ödeme yöntemi istatistikleri',
        'Kargo modu ve teslimat analizi',
        'Aylık gelir trendi (son 12 ay)',
        'Kritik stok seviyesindeki ürünler',
      ],
    },
    CORPORATE: {
      welcome:
        'Merhaba! Ben DataPulse AI Asistanım 🤖\n\n' +
        'Mağazanızın verilerine erişebilirsiniz. Sorgulayabilecekleriniz:\n' +
        '• "Mağazamın en çok satan ürünleri"\n' +
        '• "Bu ayki sipariş durumu dağılımım"\n' +
        '• "Müşterilerimin şehir dağılımı"\n' +
        '• "Aylık satış gelir trendiim"',
      suggestions: [
        'Mağazamın sipariş durum dağılımı',
        'En çok satan ürünlerim',
        'Kategori bazlı mağaza gelirim',
        'Müşterilerimin şehir dağılımı',
        'Mağazama gelen yorumlar ve puanlar',
        'Stok durumu ve kritik ürünler',
        'Aylık satış gelirim',
        'Ödeme yöntemi dağılımım',
        'Kargo modu istatistiklerim',
        'Müşteri üyelik tipi dağılımı',
      ],
    },
    INDIVIDUAL: {
      welcome:
        'Merhaba! Ben DataPulse AI Asistanım 🤖\n\n' +
        'Kendi alışveriş verilerinizi sorgulayabilirsiniz:\n' +
        '• "Siparişlerimin durumu nedir?"\n' +
        '• "Ne kadar harcadım bu ay?"\n' +
        '• "Yorumladığım ürünler"\n' +
        '• "Aylık harcama trendom"',
      suggestions: [
        'Siparişlerimin durum dağılımı',
        'Aylık harcama trendiim',
        'Toplam sipariş ve harcama özetim',
        'Benim için en çok satın aldığım ürünler',
        'Yazdığım yorumlar ve verdiğim puanlar',
        'Bekleyen veya işlemdeki siparişlerim',
        'Hangi ödeme yöntemlerini kullandım?',
        'Kargolarımın durumu',
        'Kategori bazlı harcamalarım',
      ],
    },
  };

  get roleConfig() {
    const role = this.user?.role ?? 'INDIVIDUAL';
    return this.ROLE_CONFIG[role] ?? this.ROLE_CONFIG['INDIVIDUAL'];
  }

  get suggestions() { return this.roleConfig.suggestions; }

  messages: ChatMessage[] = [];

  @ViewChild('chatScroll') private chatScrollRef!: ElementRef;

  constructor(
    private http: HttpClient,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef
  ) {
    const u = this.authService.getCurrentUser();
    this.isAdmin      = u?.role === 'ADMIN';
    this.isCorp       = u?.role === 'CORPORATE';
    this.isIndividual = !this.isAdmin && !this.isCorp;
  }

  get user() { return this.authService.getCurrentUser(); }

  ngOnInit() {
    this.loadPlotly();
    this.messages = [{ sender: 'ai', text: this.roleConfig.welcome }];
  }

  ngAfterViewChecked() {
    if (this.shouldScroll) { this.scrollToBottom(); this.shouldScroll = false; }
  }

  private scrollToBottom() {
    try { const el = this.chatScrollRef?.nativeElement; if (el) el.scrollTop = el.scrollHeight; } catch {}
  }

  private loadPlotly() {
    if (typeof Plotly !== 'undefined') return;
    const s = document.createElement('script');
    s.src = 'https://cdn.plot.ly/plotly-2.27.0.min.js';
    document.head.appendChild(s);
  }

  useSuggestion(s: string) { this.userQuery = s; this.sendMessage(); }

  sendMessage() {
    const q = this.userQuery.trim();
    if (!q || this.loading) return;

    this.messages.push({ sender: 'user', text: q });
    this.userQuery    = '';
    this.loading      = true;
    this.shouldScroll = true;
    this.cdr.detectChanges();

    const loadingMsg: ChatMessage = {
      sender: 'ai', text: '', loading: true,
      thinkingText: this.THINKING_PHASES[0]
    };
    this.messages.push(loadingMsg);
    this.shouldScroll = true;
    this.cdr.detectChanges();

    // Rotate thinking phases every 600ms while waiting
    let phaseIdx = 0;
    this.thinkingTimer = setInterval(() => {
      phaseIdx = (phaseIdx + 1) % this.THINKING_PHASES.length;
      loadingMsg.thinkingText = this.THINKING_PHASES[phaseIdx];
      this.cdr.detectChanges();
    }, 650);

    const body = { question: q };

    this.fetchViaSpring(body, loadingMsg);
  }

  private stopThinking() {
    if (this.thinkingTimer) { clearInterval(this.thinkingTimer); this.thinkingTimer = null; }
  }

  private fetchViaSpring(body: any, loadingMsg: ChatMessage) {
    // Route through Spring Boot — JWT interceptor adds Authorization header automatically.
    // Spring Boot resolves role + store_id from the authenticated principal and forwards to Python.
    this.http.post<any>(`${environment.apiUrl}/chat/ask`, body).subscribe({
      next: d => {
        this.stopThinking();
        const payload = d?.data ?? d;
        this.applyResult(loadingMsg, payload);
        this.loading      = false;
        this.shouldScroll = true;
        this.cdr.detectChanges();
      },
      error: () => {
        this.stopThinking();
        loadingMsg.loading = false;
        loadingMsg.text    = '⚠️ AI servisi şu an ulaşılamıyor.\n\nSpring Boot ve Python servislerinin çalıştığından emin olun.';
        this.loading      = false;
        this.shouldScroll = true;
        this.cdr.detectChanges();
      }
    });
  }

  private applyResult(msg: ChatMessage, payload: any) {
    msg.loading      = false;
    msg.text         = payload.answer   ?? 'Yanıt alınamadı.';
    msg.sql          = payload.sql      ?? undefined;
    msg.plotData     = payload.plotData ?? undefined;

    if (msg.plotData) {
      msg.chartId = `chart-${++this.chartCounter}`;
    }

    this.shouldScroll = true;
    this.cdr.detectChanges();

    if (msg.plotData && msg.chartId) {
      setTimeout(() => this.renderChart(msg.chartId!, msg.plotData!), 150);
    }
  }

  renderChart(chartId: string, plotDataStr: string) {
    const el = document.getElementById(chartId);
    if (!el) { setTimeout(() => this.renderChart(chartId, plotDataStr), 220); return; }
    try {
      const spec = JSON.parse(plotDataStr);
      if (typeof Plotly !== 'undefined') {
        Plotly.newPlot(el, spec.data, spec.layout, { responsive: true, displayModeBar: false });
      }
    } catch (e) { console.warn('Plotly render:', e); }
  }

  formatText(text: string): string {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
      .replace(/•/g, '&bull;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }

  logout() { this.authService.logout(); this.router.navigate(['/login']); }
}

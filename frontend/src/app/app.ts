import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { ChatWidget } from './chat-widget/chat-widget'; // Dosya adın farklıysa burayı düzelt

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, ChatWidget], // ChatWidget buraya eklendi!
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App { }

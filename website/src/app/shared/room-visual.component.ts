import { Component, Input, OnChanges } from '@angular/core';

/**
 * Placeholder room visual: the API returns no images, so we render a
 * deterministic gradient "postcard" with a line-art room icon.
 * Looks intentional, never broken.
 */
@Component({
  selector: 'app-room-visual',
  imports: [],
  template: `
    <svg
      class="room-visual"
      [attr.viewBox]="'0 0 400 260'"
      preserveAspectRatio="xMidYMid slice"
      role="img"
      [attr.aria-label]="label + ' illustration'"
    >
      <defs>
        <linearGradient [attr.id]="gradId" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" [attr.stop-color]="c1" />
          <stop offset="100%" [attr.stop-color]="c2" />
        </linearGradient>
        <radialGradient [attr.id]="glowId" cx="30%" cy="20%" r="80%">
          <stop offset="0%" stop-color="rgba(255,255,255,0.35)" />
          <stop offset="100%" stop-color="rgba(255,255,255,0)" />
        </radialGradient>
      </defs>
      <rect width="400" height="260" [attr.fill]="'url(#' + gradId + ')'" />
      <rect width="400" height="260" [attr.fill]="'url(#' + glowId + ')'" />
      <!-- rolling hills -->
      <path [attr.d]="wave1" fill="rgba(255,255,255,0.10)" />
      <path [attr.d]="wave2" fill="rgba(255,255,255,0.08)" />
      <!-- room line-art -->
      <g
        fill="none"
        stroke="rgba(255,255,255,0.85)"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
        transform="translate(148 70)"
      >
        <path d="M8 96 V44 a8 8 0 0 1 8-8 h80 a8 8 0 0 1 8 8 v52" />
        <path d="M0 96 h112" />
        <path d="M24 96 V64 a4 4 0 0 1 4-4 h24 a4 4 0 0 1 4 4 v32" />
        <path d="M72 60 h20 M72 74 h20" />
        <circle cx="48" cy="32" r="7" />
      </g>
    </svg>
  `,
  styles: `
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: var(--surface-2);
    }

    .room-visual {
      display: block;
      width: 100%;
      height: 100%;
      transition: transform 0.8s cubic-bezier(0.22, 1, 0.36, 1);
    }

    :host-context(a:hover) .room-visual,
    :host-context(.card:hover) .room-visual {
      transform: scale(1.06);
    }
  `,
})
export class RoomVisualComponent implements OnChanges {
  @Input({ required: true }) seed!: number | string;
  @Input() label = 'Room';

  protected gradId = 'rv-g';
  protected glowId = 'rv-l';
  protected c1 = '#5b8def';
  protected c2 = '#9f7aea';
  protected wave1 = '';
  protected wave2 = '';

  private readonly palettes: Array<[string, string]> = [
    ['#5b8def', '#9f7aea'],
    ['#0ea5a4', '#38bdf8'],
    ['#f59e0b', '#f472b6'],
    ['#6366f1', '#22d3ee'],
    ['#10b981', '#84cc16'],
    ['#e879a0', '#fb923c'],
    ['#8b5cf6', '#ec4899'],
  ];

  ngOnChanges(): void {
    const n = this.hash(String(this.seed ?? 0));
    const [c1, c2] = this.palettes[n % this.palettes.length];
    this.c1 = c1;
    this.c2 = c2;
    this.gradId = `rv-g-${n}`;
    this.glowId = `rv-l-${n}`;
    const a = (n % 40) - 20;
    this.wave1 = `M0 ${185 + (n % 20)} C 90 ${160 + a}, 150 ${215 - a}, 230 ${190 + (n % 15)} S 360 ${165 + a}, 400 ${185 + (n % 10)} V 260 H 0 Z`;
    this.wave2 = `M0 ${215 + (n % 12)} C 110 ${195 - a}, 190 ${240 + a}, 280 ${215} S 380 ${200}, 400 ${218} V 260 H 0 Z`;
  }

  private hash(s: string): number {
    let h = 0;
    for (let i = 0; i < s.length; i++) {
      h = (h * 31 + s.charCodeAt(i)) | 0;
    }
    return Math.abs(h);
  }
}

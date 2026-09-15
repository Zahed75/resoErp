import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Property } from '../core/models';

@Component({
  selector: 'app-footer',
  imports: [RouterLink],
  template: `
    <footer class="footer">
      <div class="container footer-grid">
        <div class="footer-brand">
          <a class="brand" routerLink="/">
            <span class="brand-text">Reso<em>Resort</em></span>
          </a>
          <p>
            A collection of handpicked retreats where modern comfort meets quiet nature.
            Book direct for the best rates, always.
          </p>
        </div>

        <div class="footer-col">
          <h4>Explore</h4>
          <a routerLink="/rooms">Rooms &amp; suites</a>
          <a routerLink="/book">Book a stay</a>
          <a routerLink="/contact">Contact us</a>
        </div>

        <div class="footer-col">
          <h4>Our properties</h4>
          @for (p of properties; track p.id) {
            <a [routerLink]="['/book']" [queryParams]="{ property_id: p.id }">{{ p.name }} · {{ p.city }}</a>
          } @empty {
            <span class="muted">Loading properties…</span>
          }
        </div>

        <div class="footer-col">
          <h4>Get in touch</h4>
          @for (p of properties; track p.id) {
            <div class="contact-line">
              <strong>{{ p.name }}</strong>
              <span>{{ p.phone }}</span>
              <span>{{ p.email }}</span>
            </div>
          } @empty {
            <span class="muted">—</span>
          }
        </div>
      </div>
      <div class="container footer-bottom">
        <span>© {{ year }} Reso Resort. All rights reserved.</span>
        <span class="muted">Crafted with a liquid touch.</span>
      </div>
    </footer>
  `,
  styles: `
    .footer {
      margin-top: 5rem;
      border-top: 1px solid var(--glass-border);
      background: var(--glass-bg);
      backdrop-filter: blur(var(--glass-blur));
      -webkit-backdrop-filter: blur(var(--glass-blur));
    }

    .footer-grid {
      display: grid;
      grid-template-columns: 1.4fr 1fr 1fr 1.2fr;
      gap: 2.5rem;
      padding: 3.5rem 0 2rem;
    }

    .footer-brand p {
      color: var(--text-secondary);
      font-size: 0.95rem;
      line-height: 1.7;
      max-width: 30ch;
      margin-top: 0.85rem;
    }

    .brand {
      font-size: 1.3rem;
      font-weight: 700;
      color: var(--text-primary);
      text-decoration: none;
      letter-spacing: -0.02em;

      em {
        font-style: normal;
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }
    }

    .footer-col {
      display: flex;
      flex-direction: column;
      gap: 0.55rem;

      h4 {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--text-muted);
        margin-bottom: 0.4rem;
      }

      a {
        color: var(--text-secondary);
        text-decoration: none;
        font-size: 0.95rem;
        transition: color var(--transition-fast), transform var(--transition-fast);

        &:hover { color: var(--accent); transform: translateX(3px); }
      }
    }

    .contact-line {
      display: flex;
      flex-direction: column;
      font-size: 0.9rem;
      color: var(--text-secondary);
      margin-bottom: 0.6rem;

      strong { color: var(--text-primary); font-weight: 600; }
    }

    .footer-bottom {
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 0.5rem;
      padding: 1.25rem 0 1.5rem;
      border-top: 1px solid var(--glass-border);
      font-size: 0.85rem;
      color: var(--text-secondary);
    }

    .muted { color: var(--text-muted); }

    @media (max-width: 900px) {
      .footer-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 560px) {
      .footer-grid { grid-template-columns: 1fr; gap: 1.75rem; }
    }
  `,
})
export class FooterComponent {
  @Input({ required: true }) properties: Property[] = [];
  protected readonly year = new Date().getFullYear();
}

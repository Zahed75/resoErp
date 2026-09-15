import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { ThemeToggleComponent } from './theme-toggle.component';

@Component({
  selector: 'app-navbar',
  imports: [RouterLink, RouterLinkActive, ThemeToggleComponent],
  template: `
    <header class="nav-wrap">
      <nav class="navbar container" aria-label="Main navigation">
        <a class="brand" routerLink="/">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M4 22c3-6 6-9 8-9s3 3 4 3 2-6 5-6 4 5 7 12" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
              <path d="M3 27h26" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity="0.5" />
            </svg>
          </span>
          <span class="brand-text">Reso<em>Resort</em></span>
        </a>

        <button
          class="nav-burger"
          type="button"
          (click)="open = !open"
          [attr.aria-expanded]="open"
          aria-label="Toggle menu"
        >
          <span></span><span></span><span></span>
        </button>

        <div class="nav-links" [class.open]="open">
          <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" (click)="open = false">Home</a>
          <a routerLink="/rooms" routerLinkActive="active" (click)="open = false">Rooms</a>
          <a routerLink="/book" routerLinkActive="active" (click)="open = false">Book</a>
          <a routerLink="/contact" routerLinkActive="active" (click)="open = false">Contact</a>
          <app-theme-toggle />
          <a class="btn btn-primary nav-cta" routerLink="/book" (click)="open = false">Reserve now</a>
        </div>
      </nav>
    </header>
  `,
  styles: `
    .nav-wrap {
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.75rem 0;
    }

    .navbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 0.6rem 1.25rem;
      border-radius: var(--radius-full);
      background: var(--glass-bg-strong);
      border: 1px solid var(--glass-border);
      backdrop-filter: blur(var(--glass-blur));
      -webkit-backdrop-filter: blur(var(--glass-blur));
      box-shadow: var(--shadow-soft);
    }

    .brand {
      display: inline-flex;
      align-items: center;
      gap: 0.55rem;
      text-decoration: none;
      color: var(--text-primary);
      font-weight: 700;
      font-size: 1.15rem;
      letter-spacing: -0.02em;

      em {
        font-style: normal;
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }
    }

    .brand-mark {
      display: inline-flex;
      width: 2rem;
      height: 2rem;
      color: var(--accent);

      svg { width: 100%; height: 100%; }
    }

    .nav-links {
      display: flex;
      align-items: center;
      gap: 1.35rem;

      a:not(.btn) {
        position: relative;
        color: var(--text-secondary);
        text-decoration: none;
        font-weight: 500;
        font-size: 0.95rem;
        transition: color var(--transition-fast);

        &::after {
          content: '';
          position: absolute;
          left: 0;
          bottom: -4px;
          width: 100%;
          height: 2px;
          border-radius: 2px;
          background: var(--accent-gradient);
          transform: scaleX(0);
          transform-origin: left;
          transition: transform var(--transition-base);
        }

        &:hover { color: var(--text-primary); }
        &:hover::after, &.active::after { transform: scaleX(1); }
        &.active { color: var(--text-primary); }
      }
    }

    .nav-cta { padding: 0.5rem 1.1rem; font-size: 0.9rem; }

    .nav-burger {
      display: none;
      flex-direction: column;
      gap: 5px;
      padding: 0.5rem;
      background: none;
      border: none;
      cursor: pointer;

      span {
        width: 22px;
        height: 2px;
        border-radius: 2px;
        background: var(--text-primary);
        transition: transform var(--transition-base), opacity var(--transition-base);
      }
    }

    @media (max-width: 768px) {
      .nav-burger { display: flex; }

      .nav-links {
        position: absolute;
        top: calc(100% + 0.5rem);
        left: 1rem;
        right: 1rem;
        flex-direction: column;
        align-items: stretch;
        gap: 0.25rem;
        padding: 1rem;
        border-radius: var(--radius-lg);
        background: var(--glass-bg-strong);
        border: 1px solid var(--glass-border);
        backdrop-filter: blur(var(--glass-blur));
        -webkit-backdrop-filter: blur(var(--glass-blur));
        box-shadow: var(--shadow-soft);
        opacity: 0;
        pointer-events: none;
        transform: translateY(-8px);
        transition: opacity var(--transition-base), transform var(--transition-base);

        &.open {
          opacity: 1;
          pointer-events: auto;
          transform: translateY(0);
        }

        a:not(.btn) { padding: 0.6rem 0.75rem; border-radius: var(--radius-sm); }
        a:not(.btn):hover { background: var(--glass-bg); }
        app-theme-toggle { align-self: center; margin: 0.35rem 0; }
        .nav-cta { text-align: center; }
      }
    }
  `,
})
export class NavbarComponent {
  protected open = false;
}

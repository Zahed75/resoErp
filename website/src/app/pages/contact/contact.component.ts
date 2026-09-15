import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { PropertyStore } from '../../shared/property-store.service';
import { RevealDirective } from '../../shared/reveal.directive';

@Component({
  selector: 'app-contact',
  imports: [FormsModule, RouterLink, RevealDirective],
  template: `
    <div class="page container contact-page">
      <header class="section">
        <h1 class="section-title"><span class="eyebrow">Get in touch</span>Contact us</h1>
        <p class="section-sub">
          Questions about a stay, an event, or a group booking? Our front desk teams at every
          property are happy to help.
        </p>
      </header>

      @if (store.error()) {
        <div class="error-banner">{{ store.error() }}</div>
      }

      <div class="contact-grid">
        <section class="cards">
          @for (p of store.properties(); track p.id; let i = $index) {
            <article class="glass-card property-card" appReveal="{{ i * 90 }}ms">
              <div class="property-head">
                <span class="chip">{{ p.code }}</span>
                <h2>{{ p.name }}</h2>
                <p class="muted">{{ p.city }}</p>
              </div>
              <ul class="contact-list">
                @if (p.phone) {
                  <li>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.2a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.8.7a2 2 0 0 1 1.7 2Z" />
                    </svg>
                    <a [href]="'tel:' + p.phone">{{ p.phone }}</a>
                  </li>
                }
                @if (p.email) {
                  <li>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="2" y="4" width="20" height="16" rx="2" />
                      <path d="m22 7-10 6L2 7" />
                    </svg>
                    <a [href]="'mailto:' + p.email">{{ p.email }}</a>
                  </li>
                }
                <li>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" />
                    <circle cx="12" cy="10" r="3" />
                  </svg>
                  <span>{{ p.city }}</span>
                </li>
              </ul>
              <a class="btn btn-ghost" [routerLink]="['/book']" [queryParams]="{ property_id: p.id }">
                Book this property
              </a>
            </article>
          } @empty {
            @if (store.loading()) {
              <div class="skeleton" style="height: 14rem; border-radius: var(--radius-lg);"></div>
              <div class="skeleton" style="height: 14rem; border-radius: var(--radius-lg);"></div>
            } @else {
              <div class="empty-state glass-card">
                <p>No properties are available right now — please try again shortly.</p>
              </div>
            }
          }
        </section>

        <section class="glass-card enquiry-card" appReveal="120ms">
          <h2>Send an enquiry</h2>
          @if (sent()) {
            <div class="success-banner">
              Thank you, {{ sentName() }}! Your message has been noted — our team will get back to
              you within a day.
            </div>
          } @else {
            <form #f="ngForm" (ngSubmit)="submit(f.valid === true)">
              <div class="field">
                <label for="c-name">Your name</label>
                <input id="c-name" name="name" [(ngModel)]="name" required minlength="2" #nameCtrl="ngModel" placeholder="e.g. Arif Chowdhury" />
                @if (nameCtrl.invalid && nameCtrl.touched) {
                  <span class="field-error">Please enter your name.</span>
                }
              </div>
              <div class="field">
                <label for="c-email">Email</label>
                <input id="c-email" type="email" name="email" [(ngModel)]="email" required email #emailCtrl="ngModel" placeholder="you@example.com" />
                @if (emailCtrl.invalid && emailCtrl.touched) {
                  <span class="field-error">Enter a valid email address.</span>
                }
              </div>
              <div class="field">
                <label for="c-message">Message</label>
                <textarea id="c-message" name="message" rows="5" [(ngModel)]="message" required minlength="10" #msgCtrl="ngModel" placeholder="Tell us about your trip…"></textarea>
                @if (msgCtrl.invalid && msgCtrl.touched) {
                  <span class="field-error">Please write a short message (10+ characters).</span>
                }
              </div>
              <button class="btn btn-primary" type="submit" [disabled]="f.invalid || sending()">
                {{ sending() ? 'Sending…' : 'Send message' }}
              </button>
            </form>
          }
        </section>
      </div>
    </div>
  `,
  styles: `
    .contact-grid {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 1.5rem;
      align-items: start;
    }

    .cards {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .property-card {
      padding: 1.5rem;

      .property-head {
        h2 { margin: 0.5rem 0 0.15rem; }
      }
    }

    .contact-list {
      list-style: none;
      margin: 1.1rem 0 1.25rem;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 0.65rem;

      li {
        display: flex;
        align-items: center;
        gap: 0.7rem;

        svg {
          width: 1.05rem;
          height: 1.05rem;
          color: var(--accent);
          flex-shrink: 0;
        }

        a {
          color: var(--text-primary);
          text-decoration: none;

          &:hover { color: var(--accent); }
        }
      }
    }

    .enquiry-card {
      padding: 1.75rem;
      position: sticky;
      top: 6rem;

      h2 { margin: 0 0 1.25rem; }

      form {
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
    }

    .field-error {
      color: var(--danger);
      font-size: 0.8rem;
    }

    @media (max-width: 900px) {
      .contact-grid { grid-template-columns: 1fr; }
      .enquiry-card { position: static; }
    }
  `,
})
export class ContactComponent {
  protected readonly store = inject(PropertyStore);

  protected name = '';
  protected email = '';
  protected message = '';

  protected readonly sending = signal(false);
  protected readonly sent = signal(false);
  protected readonly sentName = signal('');

  protected submit(valid: boolean): void {
    if (!valid || this.sending()) {
      return;
    }
    // Front-end only demo — a real CRM endpoint can be wired in later.
    this.sending.set(true);
    setTimeout(() => {
      this.sending.set(false);
      this.sentName.set(this.name.trim().split(' ')[0] || 'traveller');
      this.sent.set(true);
    }, 600);
  }
}

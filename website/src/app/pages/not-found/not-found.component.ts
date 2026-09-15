import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { RevealDirective } from '../../shared/reveal.directive';

@Component({
  selector: 'app-not-found',
  imports: [RouterLink, RevealDirective],
  template: `
    <div class="page container notfound-page">
      <div class="glass-card notfound-card" appReveal>
        <span class="eyebrow">Lost at sea?</span>
        <h1>404</h1>
        <p class="muted">The page you are looking for drifted away with the tide.</p>
        <div class="actions">
          <a class="btn btn-primary" routerLink="/">Back to home</a>
          <a class="btn btn-ghost" routerLink="/rooms">Browse rooms</a>
        </div>
      </div>
    </div>
  `,
  styles: `
    .notfound-page {
      display: flex;
      justify-content: center;
      padding-top: 6rem;
      padding-bottom: 6rem;
    }

    .notfound-card {
      max-width: 460px;
      padding: 3rem 2.5rem;
      text-align: center;

      h1 {
        font-size: 4.5rem;
        margin: 0.5rem 0;
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }
    }

    .actions {
      display: flex;
      justify-content: center;
      gap: 0.9rem;
      margin-top: 1.75rem;
      flex-wrap: wrap;
    }
  `,
})
export class NotFoundComponent {}

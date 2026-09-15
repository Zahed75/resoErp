import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { PropertyStore } from '../../shared/property-store.service';
import { RevealDirective } from '../../shared/reveal.directive';
import { RoomVisualComponent } from '../../shared/room-visual.component';
import { PricePipe } from '../../shared/price.pipe';
import { RoomTypeWithProperty } from '../../core/models';

function todayPlus(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

@Component({
  selector: 'app-home',
  imports: [FormsModule, RouterLink, RevealDirective, RoomVisualComponent, PricePipe],
  template: `
    <section class="hero">
      <div class="hero-blob blob-1" aria-hidden="true"></div>
      <div class="hero-blob blob-2" aria-hidden="true"></div>
      <div class="hero-blob blob-3" aria-hidden="true"></div>

      <div class="container hero-inner">
        <div class="hero-copy" appReveal>
          <span class="chip hero-chip">Multi-property resort collection</span>
          <h1>
            Escape to liquid
            <span class="grad-text">serenity</span>
          </h1>
          <p>
            From lakeside villas to hillside retreats — Reso Resort curates stays that flow
            around you. Transparent rates, instant confirmation, zero friction.
          </p>
        </div>

        <!-- search widget -->
        <form class="search-widget glass-card" appReveal="'120ms'" (ngSubmit)="search()">
          <div class="field">
            <label for="sw-property">Property</label>
            <select id="sw-property" name="property" [(ngModel)]="propertyId">
              <option [ngValue]="null">Any property</option>
              @for (p of store.properties(); track p.id) {
                <option [ngValue]="p.id">{{ p.name }} — {{ p.city }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="sw-checkin">Check-in</label>
            <input id="sw-checkin" type="date" name="checkin" [(ngModel)]="checkin" [min]="minDate" required />
          </div>
          <div class="field">
            <label for="sw-checkout">Check-out</label>
            <input id="sw-checkout" type="date" name="checkout" [(ngModel)]="checkout" [min]="checkin" required />
          </div>
          <div class="field">
            <label for="sw-guests">Guests</label>
            <input id="sw-guests" type="number" name="guests" [(ngModel)]="guests" min="1" max="12" required />
          </div>
          <button class="btn btn-primary search-btn" type="submit">Check availability</button>
        </form>
      </div>
    </section>

    <!-- featured rooms -->
    <section class="section container">
      <h2 class="section-title" appReveal><span class="eyebrow">Handpicked</span>Featured stays</h2>
      <p class="section-sub" appReveal="'80ms'">
        A rotating selection of our most loved rooms across every Reso property.
      </p>

      @if (store.loading()) {
        <div class="room-grid">
          @for (s of [1, 2, 3]; track s) {
            <div class="card room-card">
              <div class="room-media skeleton"></div>
              <div class="room-body">
                <div class="skeleton" style="height: 1.4rem; width: 60%;"></div>
                <div class="skeleton" style="height: 0.9rem; width: 90%;"></div>
                <div class="skeleton" style="height: 0.9rem; width: 40%;"></div>
              </div>
            </div>
          }
        </div>
      } @else if (store.error()) {
        <div class="error-banner">
          <span>⚠️</span> {{ store.error() }}
          <button class="btn btn-ghost" type="button" (click)="store.refresh()">Retry</button>
        </div>
      } @else {
        <div class="room-grid">
          @for (room of featuredRooms(); track room.id; let i = $index) {
            <a
              class="card room-card"
              appReveal="{{ i * 90 }}ms"
              [routerLink]="['/rooms', room.id]"
              [queryParams]="{ property_id: room.property_id }"
            >
              <div class="room-media">
                <app-room-visual [seed]="room.id" [label]="room.name" />
                <span class="room-prop">{{ room.property_name }}</span>
              </div>
              <div class="room-body">
                <div class="room-top">
                  <h3>{{ room.name }}</h3>
                  <span class="price">{{ room.base_price | price: room.currency }}<small>/night</small></span>
                </div>
                <p class="muted">
                  {{ room.property_city }} · sleeps {{ room.max_guests }} · {{ room.bed_type }}
                </p>
                <div class="amenity-row">
                  @for (a of room.amenities.slice(0, 3); track a) {
                    <span class="chip">{{ a }}</span>
                  }
                </div>
              </div>
            </a>
          } @empty {
            <p class="muted">No rooms are published yet — check back soon.</p>
          }
        </div>
      }
    </section>

    <!-- amenities strip -->
    <section class="section container">
      <div class="amenities-strip glass-card" appReveal>
        @for (amenity of amenityStrip; track amenity.label) {
          <div class="amenity-item">
            <span class="amenity-icon" [innerHTML]="amenity.icon"></span>
            <strong>{{ amenity.label }}</strong>
            <span class="muted">{{ amenity.sub }}</span>
          </div>
        }
      </div>
    </section>

    <!-- why stay with us -->
    <section class="section container why">
      <h2 class="section-title" appReveal><span class="eyebrow">Why Reso</span>Stay with us, stay fluid</h2>
      <div class="why-grid">
        @for (stat of stats; track stat.label; let i = $index) {
          <div class="why-card glass-card" appReveal="{{ i * 100 }}ms">
            <span class="stat-num">{{ counters()[i] }}{{ stat.suffix }}</span>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
        }
      </div>
    </section>
  `,
  styles: `
    /* ------------------------------------------------------------- hero */

    .hero {
      position: relative;
      overflow: hidden;
      padding: 4.5rem 0 3rem;
    }

    .hero-inner {
      position: relative;
      z-index: 1;
      display: flex;
      flex-direction: column;
      gap: 2.5rem;
    }

    .hero-copy {
      max-width: 640px;

      h1 {
        font-size: clamp(2.4rem, 6vw, 4.2rem);
        font-weight: 800;
        margin: 0.9rem 0 1rem;
      }

      p {
        color: var(--text-secondary);
        font-size: 1.1rem;
        max-width: 46ch;
      }
    }

    .grad-text {
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }

    .hero-chip {
      background: var(--glass-bg);
      border: 1px solid var(--glass-border);
      backdrop-filter: blur(var(--glass-blur));
      -webkit-backdrop-filter: blur(var(--glass-blur));
      color: var(--text-primary);
    }

    /* floating gradient blobs */
    .hero-blob {
      position: absolute;
      border-radius: 50%;
      filter: blur(70px);
      opacity: 0.55;
      pointer-events: none;
      animation: blob-float 14s ease-in-out infinite alternate;

      &.blob-1 {
        width: 26rem;
        height: 26rem;
        top: -8rem;
        right: -4rem;
        background: radial-gradient(circle at 30% 30%, var(--accent), transparent 70%);
      }

      &.blob-2 {
        width: 20rem;
        height: 20rem;
        bottom: -6rem;
        left: 22%;
        background: radial-gradient(circle at 60% 40%, var(--accent-2), transparent 70%);
        animation-delay: -4s;
      }

      &.blob-3 {
        width: 15rem;
        height: 15rem;
        top: 30%;
        left: -5rem;
        background: radial-gradient(circle at 50% 50%, #22c1c3, transparent 70%);
        animation-delay: -8s;
      }
    }

    @keyframes blob-float {
      from {
        transform: translate3d(0, 0, 0) scale(1);
      }
      to {
        transform: translate3d(2.5rem, -1.8rem, 0) scale(1.12);
      }
    }

    /* ------------------------------------------------- search widget */

    .search-widget {
      display: grid;
      grid-template-columns: 1.4fr 1fr 1fr 0.7fr auto;
      gap: 1rem;
      align-items: end;
      padding: 1.25rem 1.4rem;
      max-width: 1020px;
    }

    .search-btn {
      height: 2.85rem;
      white-space: nowrap;
    }

    @media (max-width: 900px) {
      .search-widget {
        grid-template-columns: 1fr 1fr;
      }
      .search-btn {
        grid-column: 1 / -1;
      }
    }

    @media (max-width: 540px) {
      .search-widget {
        grid-template-columns: 1fr;
      }
    }

    /* ------------------------------------------------------- room grid */

    .room-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1.5rem;
      margin-top: 2rem;
    }

    .room-card {
      display: flex;
      flex-direction: column;
      text-decoration: none;
      color: inherit;
    }

    .room-media {
      position: relative;
      aspect-ratio: 400 / 240;
      overflow: hidden;
    }

    .room-prop {
      position: absolute;
      left: 0.85rem;
      bottom: 0.85rem;
      padding: 0.28rem 0.8rem;
      border-radius: var(--radius-full);
      background: rgba(10, 15, 30, 0.55);
      color: #fff;
      font-size: 0.75rem;
      font-weight: 600;
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
    }

    .room-body {
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      padding: 1.1rem 1.25rem 1.35rem;
    }

    .room-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 0.75rem;

      h3 {
        margin: 0;
        font-size: 1.15rem;
      }
    }

    .price {
      font-weight: 700;
      color: var(--accent);
      white-space: nowrap;

      small {
        color: var(--text-muted);
        font-weight: 500;
        margin-left: 2px;
      }
    }

    .amenity-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    /* ------------------------------------------------- amenities strip */

    .amenities-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1.5rem;
      padding: 2rem 2.25rem;
      margin-top: 1.5rem;
    }

    .amenity-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 0.3rem;
      font-size: 0.95rem;
      transition: transform var(--transition-base);

      &:hover {
        transform: translateY(-4px);
      }

      .muted {
        font-size: 0.82rem;
      }
    }

    .amenity-icon {
      display: inline-flex;
      width: 3rem;
      height: 3rem;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-full);
      background: var(--accent-soft);
      color: var(--accent);
      margin-bottom: 0.4rem;

      ::ng-deep svg {
        width: 1.5rem;
        height: 1.5rem;
      }
    }

    /* ------------------------------------------------------------ why */

    .why-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
      margin-top: 2rem;
    }

    .why-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 2rem 1rem;
      text-align: center;
      transition: transform var(--transition-base);

      &:hover {
        transform: translateY(-5px);
      }
    }

    .stat-num {
      font-size: clamp(2rem, 4vw, 2.8rem);
      font-weight: 800;
      background: var(--accent-gradient);
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }

    .stat-label {
      color: var(--text-secondary);
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }
  `,
})
export class HomeComponent {
  protected readonly store = inject(PropertyStore);
  private readonly router = inject(Router);

  protected readonly minDate = todayPlus(0);
  protected propertyId: number | null = null;
  protected checkin = todayPlus(7);
  protected checkout = todayPlus(9);
  protected guests = 2;

  protected readonly featuredRooms = computed<RoomTypeWithProperty[]>(() =>
    this.store.allRooms().slice(0, 4),
  );

  protected readonly amenityStrip = [
    {
      label: 'Free high-speed WiFi',
      sub: 'In every room',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M2.5 9a15 15 0 0 1 19 0M5.5 12.5a10 10 0 0 1 13 0M8.5 16a5 5 0 0 1 7 0"/><circle cx="12" cy="19.5" r="1.4" fill="currentColor" stroke="none"/></svg>',
    },
    {
      label: 'Flexible check-in',
      sub: 'Late arrivals welcome',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/></svg>',
    },
    {
      label: 'Local experiences',
      sub: 'Curated by our hosts',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-7-4.6-7-10a7 7 0 0 1 14 0c0 5.4-7 10-7 10Z"/><circle cx="12" cy="11" r="2.6"/></svg>',
    },
    {
      label: 'Secure payments',
      sub: 'bKash, Nagad, cards',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.8 19 5.5v5.2c0 4.6-3 8.2-7 9.9-4-1.7-7-5.3-7-9.9V5.5L12 2.8Z"/><path d="m8.8 11.8 2.2 2.2 4.2-4.2"/></svg>',
    },
  ];

  protected readonly stats = [
    { target: 4, suffix: '', label: 'Distinct properties' },
    { target: 25, suffix: '+', label: 'Room types' },
    { target: 12, suffix: 'k+', label: 'Happy guests' },
    { target: 98, suffix: '%', label: 'Would return' },
  ];

  protected counters = signal<number[]>(this.stats.map(() => 0));

  constructor() {
    this.animateCounters();
  }

  private animateCounters(): void {
    // Counters run once on load; 1.4s ease-out count-up.
    const duration = 1400;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      this.counters.set(this.stats.map((s) => Math.round(s.target * eased)));
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  protected search(): void {
    if (!this.checkin || !this.checkout) {
      return;
    }
    const params: Record<string, string | number> = {
      checkin: this.checkin,
      checkout: this.checkout,
      guests: this.guests,
    };
    if (this.propertyId != null) {
      params['property_id'] = this.propertyId;
    }
    void this.router.navigate(['/book'], { queryParams: params });
  }
}

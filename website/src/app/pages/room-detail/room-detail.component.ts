import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AvailabilityResult, RoomTypeWithProperty } from '../../core/models';
import { PropertyStore } from '../../shared/property-store.service';
import { RevealDirective } from '../../shared/reveal.directive';
import { RoomVisualComponent } from '../../shared/room-visual.component';
import { PricePipe } from '../../shared/price.pipe';

function todayPlus(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function nightsBetween(a: string, b: string): number {
  const ms = new Date(b).getTime() - new Date(a).getTime();
  return Math.round(ms / 86400000);
}

@Component({
  selector: 'app-room-detail',
  imports: [FormsModule, RouterLink, RevealDirective, RoomVisualComponent, PricePipe],
  template: `
    @if (room(); as room) {
      <div class="page container detail-grid">
        <div class="detail-media card" appReveal>
          <app-room-visual [seed]="room.id" [label]="room.name" />
        </div>

        <div class="detail-info" appReveal="'100ms'">
          <span class="chip">{{ room.property_name }} · {{ room.property_city }}</span>
          <h1>{{ room.name }}</h1>
          <p class="muted">
            Sleeps up to {{ room.max_guests }} guests · {{ room.bed_type }} bed
          </p>

          <h3>Amenities</h3>
          <div class="amenity-row">
            @for (a of room.amenities; track a) {
              <span class="chip">{{ a }}</span>
            } @empty {
              <span class="muted">Amenities to be announced.</span>
            }
          </div>

          <!-- price calculator -->
          <div class="calculator glass-card">
            <h3>Price calculator</h3>
            <div class="calc-fields">
              <div class="field">
                <label for="d-checkin">Check-in</label>
                <input id="d-checkin" type="date" [(ngModel)]="checkin" [min]="minDate" (ngModelChange)="recalc()" />
              </div>
              <div class="field">
                <label for="d-checkout">Check-out</label>
                <input id="d-checkout" type="date" [(ngModel)]="checkout" [min]="checkin" (ngModelChange)="recalc()" />
              </div>
              <div class="field">
                <label for="d-guests">Guests</label>
                <input id="d-guests" type="number" min="1" [max]="room.max_guests" [(ngModel)]="guests" (ngModelChange)="recalc()" />
              </div>
            </div>

            @if (calcError()) {
              <div class="error-banner">{{ calcError() }}</div>
            } @else if (calcLoading()) {
              <div class="calc-result skeleton" style="height: 3.2rem;"></div>
            } @else if (quote(); as q) {
              <div class="calc-result">
                <div>
                  <span class="muted">{{ nights() }} night{{ nights() === 1 ? '' : 's' }} · {{ q.available_count }} available</span>
                  <strong>{{ q.total_price | price: q.currency }}</strong>
                  <span class="muted">{{ q.price_per_night | price: q.currency }} / night</span>
                </div>
                <a
                  class="btn btn-primary"
                  [routerLink]="['/book']"
                  [queryParams]="{
                    property_id: room.property_id,
                    room_type_id: room.id,
                    checkin: checkin,
                    checkout: checkout,
                    guests: guests
                  }"
                >Book now</a>
              </div>
            } @else {
              <p class="muted">Pick your dates to see live pricing.</p>
            }
          </div>

          <p class="muted fine-print">
            Check-in from {{ propertyCheckin }} · check-out by {{ propertyCheckout }}
          </p>
        </div>
      </div>
    } @else if (store.loading()) {
      <div class="page container detail-grid">
        <div class="skeleton" style="aspect-ratio: 400 / 260; border-radius: var(--radius-lg);"></div>
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div class="skeleton" style="height: 2rem; width: 70%;"></div>
          <div class="skeleton" style="height: 1rem; width: 90%;"></div>
          <div class="skeleton" style="height: 1rem; width: 50%;"></div>
          <div class="skeleton" style="height: 8rem;"></div>
        </div>
      </div>
    } @else {
      <div class="page container not-found">
        <div class="glass-card empty-card">
          <h1>Room not found</h1>
          <p class="muted">This room type doesn't exist (or was just retired).</p>
          <a class="btn btn-primary" routerLink="/rooms">Browse all rooms</a>
        </div>
      </div>
    }
  `,
  styles: `
    .detail-grid {
      display: grid;
      grid-template-columns: 1.05fr 1fr;
      gap: 2.5rem;
      align-items: start;
    }

    .detail-media {
      aspect-ratio: 400 / 300;
    }

    .detail-info {
      h1 { font-size: clamp(1.8rem, 4vw, 2.6rem); margin: 0.7rem 0 0.25rem; }
      h3 { margin-top: 1.4rem; font-size: 1.05rem; }
    }

    .amenity-row { display: flex; flex-wrap: wrap; gap: 0.45rem; }

    .calculator {
      margin-top: 1.75rem;
      padding: 1.5rem;

      h3 { margin-top: 0; }
    }

    .calc-fields {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.9rem;
      margin-bottom: 1.1rem;
    }

    .calc-result {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-radius: var(--radius-md);
      background: var(--accent-soft);

      > div {
        display: flex;
        flex-direction: column;
        line-height: 1.4;
      }

      strong {
        font-size: 1.5rem;
        color: var(--accent);
      }
    }

    .fine-print { margin-top: 1.25rem; font-size: 0.85rem; }

    .not-found { padding-top: 4rem; }
    .empty-card {
      max-width: 480px;
      margin-inline: auto;
      padding: 3rem;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
    }

    @media (max-width: 860px) {
      .detail-grid { grid-template-columns: 1fr; }
      .calc-fields { grid-template-columns: 1fr; }
      .calc-result { flex-direction: column; align-items: stretch; text-align: center; }
    }
  `,
})
export class RoomDetailComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly store = inject(PropertyStore);
  private readonly api = inject(ApiService);

  protected readonly minDate = todayPlus(0);
  protected checkin = todayPlus(7);
  protected checkout = todayPlus(9);
  protected guests = 2;

  protected readonly calcLoading = signal(false);
  protected readonly calcError = signal<string | null>(null);
  protected readonly quote = signal<AvailabilityResult | null>(null);

  private readonly roomTypeId = signal<number | null>(null);

  protected readonly room = computed<RoomTypeWithProperty | null>(() => {
    const id = this.roomTypeId();
    return id == null ? null : (this.store.allRooms().find((r) => r.id === id) ?? null);
  });

  protected readonly nights = computed(() =>
    this.checkin && this.checkout ? Math.max(0, nightsBetween(this.checkin, this.checkout)) : 0,
  );

  protected get propertyCheckin(): string {
    return this.room() ? (this.store.propertyById(this.room()!.property_id)?.checkin_time ?? '—') : '—';
  }
  protected get propertyCheckout(): string {
    return this.room() ? (this.store.propertyById(this.room()!.property_id)?.checkout_time ?? '—') : '—';
  }

  constructor() {
    const idParam = this.route.snapshot.paramMap.get('roomTypeId');
    const id = idParam ? Number(idParam) : NaN;
    if (!Number.isFinite(id)) {
      void this.router.navigate(['/rooms']);
      return;
    }
    this.roomTypeId.set(id);
    this.recalc();
  }

  protected recalc(): void {
    const room = this.room();
    if (!room || !this.checkin || !this.checkout || this.nights() < 1) {
      this.quote.set(null);
      this.calcError.set(null);
      if (this.checkin && this.checkout && this.nights() < 1) {
        this.calcError.set('Check-out must be after check-in.');
      }
      return;
    }

    this.calcLoading.set(true);
    this.calcError.set(null);
    this.api
      .checkAvailability({
        property_id: room.property_id,
        checkin_date: this.checkin,
        checkout_date: this.checkout,
        guests: this.guests,
        room_type_id: room.id,
      })
      .subscribe({
        next: (results) => {
          this.calcLoading.set(false);
          this.quote.set(results.find((r) => r.room_type_id === room.id) ?? null);
          if (!this.quote()) {
            this.calcError.set('No availability for these dates. Try different dates or fewer guests.');
          }
        },
        error: (err: unknown) => {
          this.calcLoading.set(false);
          this.calcError.set(err instanceof Error ? err.message : 'Could not check availability.');
        },
      });
  }
}

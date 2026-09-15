import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PropertyStore } from '../../shared/property-store.service';
import { RevealDirective } from '../../shared/reveal.directive';
import { RoomVisualComponent } from '../../shared/room-visual.component';
import { PricePipe } from '../../shared/price.pipe';
import { RoomTypeWithProperty } from '../../core/models';

@Component({
  selector: 'app-rooms',
  imports: [FormsModule, RouterLink, RevealDirective, RoomVisualComponent, PricePipe],
  template: `
    <div class="page container">
      <header class="rooms-head">
        <div>
          <h1 class="section-title"><span class="eyebrow">Rooms &amp; suites</span>Find your room</h1>
          <p class="section-sub">Every room type across every Reso property, in one place.</p>
        </div>

        <div class="filters glass-card">
          <div class="field">
            <label for="f-property">Property</label>
            <select id="f-property" [(ngModel)]="propertyFilter">
              <option [ngValue]="null">All properties</option>
              @for (p of store.properties(); track p.id) {
                <option [ngValue]="p.id">{{ p.name }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="f-guests">Min. guests</label>
            <input id="f-guests" type="number" min="1" max="12" [(ngModel)]="guestsFilter" />
          </div>
          <button class="btn btn-ghost" type="button" (click)="reset()">Reset</button>
        </div>
      </header>

      @if (store.loading()) {
        <div class="rooms-group">
          @for (s of [1, 2, 3, 4]; track s) {
            <div class="card room-card">
              <div class="room-media skeleton"></div>
              <div class="room-body">
                <div class="skeleton" style="height: 1.3rem; width: 55%;"></div>
                <div class="skeleton" style="height: 0.85rem; width: 85%;"></div>
                <div class="skeleton" style="height: 0.85rem; width: 35%;"></div>
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
        @for (group of groupedRooms(); track group.property.id) {
          <section class="rooms-section">
            <h2>
              {{ group.property.name }}
              <span class="muted">{{ group.property.city }}</span>
            </h2>
            <div class="rooms-group">
              @for (room of group.rooms; track room.id; let i = $index) {
                <a
                  class="card room-card"
                  appReveal="{{ i * 80 }}ms"
                  [routerLink]="['/rooms', room.id]"
                  [queryParams]="{ property_id: room.property_id }"
                >
                  <div class="room-media">
                    <app-room-visual [seed]="room.id" [label]="room.name" />
                  </div>
                  <div class="room-body">
                    <div class="room-top">
                      <h3>{{ room.name }}</h3>
                      <span class="price">{{ room.base_price | price: room.currency }}<small>/night</small></span>
                    </div>
                    <p class="muted">Sleeps {{ room.max_guests }} · {{ room.bed_type }}</p>
                    <div class="amenity-row">
                      @for (a of room.amenities.slice(0, 4); track a) {
                        <span class="chip">{{ a }}</span>
                      }
                    </div>
                  </div>
                </a>
              }
            </div>
          </section>
        } @empty {
          <div class="empty-state glass-card">
            <p>No rooms match your filters.</p>
            <button class="btn btn-ghost" type="button" (click)="reset()">Clear filters</button>
          </div>
        }
      }
    </div>
  `,
  styles: `
    .rooms-head {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 1.5rem;
    }

    .filters {
      display: flex;
      align-items: flex-end;
      gap: 0.9rem;
      padding: 1rem 1.25rem;

      .field { min-width: 150px; }
    }

    .rooms-section {
      margin-top: 3rem;

      h2 {
        font-size: 1.4rem;
        display: flex;
        align-items: baseline;
        gap: 0.6rem;

        .muted { font-size: 0.95rem; font-weight: 500; }
      }
    }

    .rooms-group {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1.5rem;
      margin-top: 1.25rem;
    }

    .room-card {
      display: flex;
      flex-direction: column;
      text-decoration: none;
      color: inherit;
    }

    .room-media {
      aspect-ratio: 400 / 240;
      overflow: hidden;
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

      h3 { margin: 0; font-size: 1.15rem; }
    }

    .price {
      font-weight: 700;
      color: var(--accent);
      white-space: nowrap;

      small { color: var(--text-muted); font-weight: 500; margin-left: 2px; }
    }

    .amenity-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }

    .empty-state {
      margin-top: 3rem;
      padding: 3rem;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 1rem;
    }

    @media (max-width: 640px) {
      .filters { flex-direction: column; align-items: stretch; width: 100%; }
    }
  `,
})
export class RoomsComponent {
  protected readonly store = inject(PropertyStore);

  private readonly propertyFilterSig = signal<number | null>(null);
  private readonly guestsFilterSig = signal<number | null>(null);

  protected get propertyFilter(): number | null {
    return this.propertyFilterSig();
  }
  protected set propertyFilter(v: number | null) {
    this.propertyFilterSig.set(v);
  }
  protected get guestsFilter(): number | null {
    return this.guestsFilterSig();
  }
  protected set guestsFilter(v: number | null) {
    this.guestsFilterSig.set(v);
  }

  protected readonly groupedRooms = computed(() => {
    const properties = this.store.properties();
    const propertyFilter = this.propertyFilterSig();
    const guestsFilter = this.guestsFilterSig();
    return properties
      .map((property) => ({
        property,
        rooms: property.room_types
          .map((r) => ({
            ...r,
            property_id: property.id,
            property_name: property.name,
            property_city: property.city,
          }))
          .filter(
            (r) =>
              (propertyFilter == null || r.property_id === propertyFilter) &&
              (guestsFilter == null || r.max_guests >= guestsFilter),
          ) as RoomTypeWithProperty[],
      }))
      .filter((g) => g.rooms.length > 0);
  });

  protected reset(): void {
    this.propertyFilterSig.set(null);
    this.guestsFilterSig.set(null);
  }
}

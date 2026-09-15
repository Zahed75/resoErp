import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import {
  AvailabilityResult,
  BookingCreated,
  PaymentMethod,
  PaymentResult,
} from '../../core/models';
import { PropertyStore } from '../../shared/property-store.service';
import { RevealDirective } from '../../shared/reveal.directive';
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

interface PaymentOption {
  id: PaymentMethod;
  name: string;
  blurb: string;
  brandVar: string;
  initials: string;
}

@Component({
  selector: 'app-book',
  imports: [FormsModule, RouterLink, RevealDirective, PricePipe],
  template: `
    <div class="page container book-page">
      <header class="book-head">
        <h1 class="section-title"><span class="eyebrow">Reservations</span>Book your stay</h1>

        @if (!confirmation()) {
          <div class="steps" aria-hidden="true">
            <span class="step" [class.active]="step() === 1" [class.done]="step() > 1">1 · Dates &amp; room</span>
            <span class="step-sep"></span>
            <span class="step" [class.active]="step() === 2">2 · Details &amp; payment</span>
          </div>
        }
      </header>

      <!-- ================= SUCCESS ================= -->
      @if (confirmation(); as c) {
        <div class="success-card glass-card" appReveal>
          <svg class="check-pop" viewBox="0 0 60 60" aria-hidden="true">
            <circle cx="30" cy="30" r="26.5" />
            <path d="M18 31.5 26.5 40 42 22" />
          </svg>
          <h2>Booking confirmed</h2>
          <p class="muted">
            Payment of <strong>{{ c.booking.amount_total | price: c.booking.currency }}</strong> received via
            {{ methodName(c.booking.payment_method) }}. A confirmation has been sent to
            {{ c.booking.guest_email }}.
          </p>

          <div class="ref-grid">
            <div><span class="muted">Booking reference</span><strong>{{ c.booking.booking_reference }}</strong></div>
            <div><span class="muted">Guest</span><strong>{{ c.booking.guest_name }}</strong></div>
            <div><span class="muted">Dates</span><strong>{{ checkin }} → {{ checkout }}</strong></div>
            <div><span class="muted">Status</span><span class="badge badge-success">{{ c.payment.state }}</span></div>
          </div>

          <div class="success-actions">
            <a class="btn btn-primary" routerLink="/">Back to home</a>
            <button class="btn btn-ghost" type="button" (click)="startOver()">Make another booking</button>
          </div>
        </div>
      } @else {

        <!-- ================= STEP 1: dates & room ================= -->
        <section class="glass-card search-panel" appReveal>
          <div class="field">
            <label for="b-property">Property</label>
            <select id="b-property" [(ngModel)]="propertyId" (ngModelChange)="availability.set(null); selectedRoomTypeId.set(null)">
              @for (p of store.properties(); track p.id) {
                <option [ngValue]="p.id">{{ p.name }} — {{ p.city }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="b-checkin">Check-in</label>
            <input id="b-checkin" type="date" [(ngModel)]="checkin" [min]="minDate" (ngModelChange)="availability.set(null)" />
          </div>
          <div class="field">
            <label for="b-checkout">Check-out</label>
            <input id="b-checkout" type="date" [(ngModel)]="checkout" [min]="checkin" (ngModelChange)="availability.set(null)" />
          </div>
          <div class="field">
            <label for="b-guests">Guests</label>
            <input id="b-guests" type="number" min="1" max="12" [(ngModel)]="guests" (ngModelChange)="availability.set(null)" />
          </div>
          <button class="btn btn-primary" type="button" [disabled]="availLoading()" (click)="searchAvailability()">
            {{ availLoading() ? 'Checking…' : 'Check availability' }}
          </button>
        </section>

        @if (formError()) {
          <div class="error-banner" style="margin-top: 1.25rem;">{{ formError() }}</div>
        }

        @if (availLoading()) {
          <div class="results-list">
            @for (s of [1, 2, 3]; track s) {
              <div class="skeleton" style="height: 6.5rem; border-radius: var(--radius-lg);"></div>
            }
          </div>
        } @else if (availError()) {
          <div class="error-banner" style="margin-top: 1.25rem;">
            <span>⚠️</span> {{ availError() }}
          </div>
        } @else if (availability(); as results) {
          <div class="results-list">
            @for (r of results; track r.room_type_id; let i = $index) {
              <button
                type="button"
                class="result-card glass-card"
                [class.selected]="selectedRoomTypeId() === r.room_type_id"
                appReveal="{{ i * 70 }}ms"
                (click)="selectRoom(r)"
              >
                <div class="result-main">
                  <strong>{{ r.name }}</strong>
                  <span class="muted">
                    {{ nights() }} night{{ nights() === 1 ? '' : 's' }} · {{ r.available_count }} room{{ r.available_count === 1 ? '' : 's' }} left
                  </span>
                </div>
                <div class="result-price">
                  <strong>{{ r.total_price | price: r.currency }}</strong>
                  <span class="muted">{{ r.price_per_night | price: r.currency }} / night</span>
                </div>
              </button>
            } @empty {
              <div class="empty-state glass-card">
                <p>No rooms available for these dates and guest count.</p>
                <p class="muted">Try different dates, another property, or fewer guests.</p>
              </div>
            }
          </div>
        }

        <!-- ================= STEP 2: guest + payment ================= -->
        @if (selectedRoomTypeId() != null && availability()) {
          <section class="glass-card guest-panel" appReveal>
            <h2>Guest details</h2>
            <form #guestForm="ngForm" (ngSubmit)="submit()">
              <div class="guest-grid">
                <div class="field">
                  <label for="g-name">Full name</label>
                  <input id="g-name" name="name" [(ngModel)]="guestName" required minlength="2" #nameCtrl="ngModel" placeholder="e.g. Nusrat Jahan" />
                  @if (nameCtrl.invalid && nameCtrl.touched) {
                    <span class="field-error">Please enter your name.</span>
                  }
                </div>
                <div class="field">
                  <label for="g-email">Email</label>
                  <input id="g-email" type="email" name="email" [(ngModel)]="guestEmail" required email #emailCtrl="ngModel" placeholder="you@example.com" />
                  @if (emailCtrl.invalid && emailCtrl.touched) {
                    <span class="field-error">Enter a valid email address.</span>
                  }
                </div>
                <div class="field">
                  <label for="g-phone">Phone</label>
                  <input id="g-phone" type="tel" name="phone" [(ngModel)]="guestPhone" required minlength="6" #phoneCtrl="ngModel" placeholder="+880 1XXX XXXXXX" />
                  @if (phoneCtrl.invalid && phoneCtrl.touched) {
                    <span class="field-error">Enter a valid phone number.</span>
                  }
                </div>
              </div>

              <h2>Payment method</h2>
              <div class="pay-grid" role="radiogroup" aria-label="Payment method">
                @for (opt of paymentOptions; track opt.id) {
                  <button
                    type="button"
                    class="pay-card"
                    [class.selected]="paymentMethod === opt.id"
                    [style.--brand]="opt.brandVar"
                    (click)="paymentMethod = opt.id"
                    role="radio"
                    [attr.aria-checked]="paymentMethod === opt.id"
                  >
                    <span class="pay-mark">{{ opt.initials }}</span>
                    <span class="pay-text">
                      <strong>{{ opt.name }}</strong>
                      <span class="muted">{{ opt.blurb }}</span>
                    </span>
                  </button>
                }
              </div>

              <div class="summary-row">
                <span class="muted">
                  {{ selectedResult()?.name }} · {{ nights() }} night{{ nights() === 1 ? '' : 's' }} · {{ guests }} guest{{ guests === 1 ? '' : 's' }}
                </span>
                <strong>{{ selectedResult()?.total_price | price: selectedResult()?.currency }}</strong>
              </div>

              <button
                class="btn btn-primary submit-btn"
                type="submit"
                [disabled]="guestForm.invalid || submitting()"
              >
                @if (submitting()) {
                  {{ paymentProcessing() ? 'Processing payment…' : 'Creating booking…' }}
                } @else {
                  Pay {{ selectedResult()?.total_price | price: selectedResult()?.currency }} &amp; confirm
                }
              </button>

              @if (submitError()) {
                <div class="error-banner" style="margin-top: 1rem;">{{ submitError() }}</div>
              }
            </form>
          </section>
        }
      }
    </div>
  `,
  styles: `
    .book-head {
      .steps {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin-top: 1rem;

        .step {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-muted);
          transition: color var(--transition-base);

          &.active { color: var(--accent); }
          &.done { color: var(--success); }
        }

        .step-sep {
          width: 2.2rem;
          height: 1px;
          background: var(--glass-border);
        }
      }
    }

    /* step 1 */
    .search-panel {
      display: grid;
      grid-template-columns: 1.4fr 1fr 1fr 0.7fr auto;
      gap: 1rem;
      align-items: end;
      padding: 1.25rem 1.4rem;
      margin-top: 1.75rem;
    }

    .results-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
      margin-top: 1.5rem;
    }

    .result-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1.5rem;
      width: 100%;
      padding: 1.25rem 1.5rem;
      text-align: left;
      font-family: inherit;
      color: inherit;
      cursor: pointer;
      transition:
        transform var(--transition-fast),
        border-color var(--transition-fast),
        box-shadow var(--transition-fast);

      &:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-lift);
      }

      &.selected {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px var(--accent-soft), var(--shadow-soft);
      }
    }

    .result-main {
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      font-size: 1.05rem;
    }

    .result-price {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      line-height: 1.35;

      strong { font-size: 1.3rem; color: var(--accent); }
    }

    .empty-state {
      padding: 2.5rem;
      text-align: center;
    }

    /* step 2 */
    .guest-panel {
      margin-top: 1.75rem;
      padding: 1.75rem;

      h2 { font-size: 1.2rem; margin: 0 0 1rem; }
    }

    .guest-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
      margin-bottom: 1.75rem;
    }

    .field-error {
      color: var(--danger);
      font-size: 0.8rem;
    }

    .pay-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 0.9rem;
      margin-bottom: 1.5rem;
    }

    .pay-card {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      padding: 0.95rem 1.1rem;
      border-radius: var(--radius-md);
      border: 1.5px solid var(--glass-border);
      background: var(--field-bg);
      font-family: inherit;
      color: inherit;
      text-align: left;
      cursor: pointer;
      transition:
        transform var(--transition-fast),
        border-color var(--transition-fast),
        box-shadow var(--transition-fast);

      &:hover { transform: translateY(-3px); }

      &.selected {
        border-color: var(--brand);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand) 22%, transparent);
      }
    }

    .pay-mark {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 2.6rem;
      height: 2.6rem;
      border-radius: var(--radius-sm);
      background: var(--brand);
      color: #fff;
      font-weight: 800;
      font-size: 0.95rem;
      flex-shrink: 0;
    }

    .pay-text {
      display: flex;
      flex-direction: column;
      line-height: 1.3;

      .muted { font-size: 0.78rem; }
    }

    .summary-row {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-radius: var(--radius-md);
      background: var(--accent-soft);
      margin-bottom: 1.25rem;

      strong { font-size: 1.35rem; color: var(--accent); }
    }

    .submit-btn { width: 100%; }

    /* success */
    .success-card {
      max-width: 620px;
      margin: 2.5rem auto 0;
      padding: 2.75rem 2.5rem;
      text-align: center;

      h2 { margin-top: 1rem; }
    }

    .ref-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin: 1.75rem 0;
      text-align: left;

      > div {
        display: flex;
        flex-direction: column;
        padding: 0.9rem 1.1rem;
        border-radius: var(--radius-md);
        background: var(--surface-2);
        line-height: 1.4;
      }
    }

    .success-actions {
      display: flex;
      justify-content: center;
      gap: 0.9rem;
      flex-wrap: wrap;
    }

    @media (max-width: 900px) {
      .search-panel { grid-template-columns: 1fr 1fr; }
      .guest-grid { grid-template-columns: 1fr; }
    }

    @media (max-width: 560px) {
      .search-panel { grid-template-columns: 1fr; }
      .result-card { flex-direction: column; align-items: flex-start; }
      .result-price { align-items: flex-start; }
      .ref-grid { grid-template-columns: 1fr; }
    }
  `,
})
export class BookComponent {
  private readonly route = inject(ActivatedRoute);
  protected readonly store = inject(PropertyStore);
  private readonly api = inject(ApiService);

  protected readonly minDate = todayPlus(0);

  protected propertyId: number | null = null;
  protected checkin = todayPlus(7);
  protected checkout = todayPlus(9);
  protected guests = 2;

  protected readonly availability = signal<AvailabilityResult[] | null>(null);
  protected readonly availLoading = signal(false);
  protected readonly availError = signal<string | null>(null);
  protected readonly selectedRoomTypeId = signal<number | null>(null);

  protected guestName = '';
  protected guestEmail = '';
  protected guestPhone = '';
  protected paymentMethod: PaymentMethod = 'bkash';

  protected readonly submitting = signal(false);
  protected readonly paymentProcessing = signal(false);
  protected readonly submitError = signal<string | null>(null);
  protected readonly confirmation = signal<{
    booking: BookingCreated & { payment_method?: PaymentMethod; guest_email?: string };
    payment: PaymentResult;
  } | null>(null);

  protected readonly paymentOptions: PaymentOption[] = [
    { id: 'bkash', name: 'bKash', blurb: 'Pay from your bKash wallet', brandVar: 'var(--brand-bkash)', initials: 'bK' },
    { id: 'nagad', name: 'Nagad', blurb: 'Pay from your Nagad account', brandVar: 'var(--brand-nagad)', initials: 'Na' },
    { id: 'sslcommerz', name: 'SSLCommerz', blurb: 'Cards & internet banking', brandVar: 'var(--brand-sslcommerz)', initials: 'SS' },
    { id: 'stripe', name: 'Stripe', blurb: 'International cards', brandVar: 'var(--brand-stripe)', initials: 'St' },
  ];

  protected readonly step = computed(() => (this.selectedRoomTypeId() != null ? 2 : 1));

  protected readonly selectedResult = computed<AvailabilityResult | null>(() => {
    const id = this.selectedRoomTypeId();
    return this.availability()?.find((r) => r.room_type_id === id) ?? null;
  });

  protected readonly nights = computed(() =>
    this.checkin && this.checkout ? Math.max(0, nightsBetween(this.checkin, this.checkout)) : 0,
  );

  protected get formError(): () => string | null {
    return this.availError;
  }

  constructor() {
    const q = this.route.snapshot.queryParamMap;
    const propertyParam = Number(q.get('property_id'));
    const roomParam = Number(q.get('room_type_id'));
    this.propertyId = Number.isFinite(propertyParam) && propertyParam > 0 ? propertyParam : null;
    this.checkin = q.get('checkin') ?? this.checkin;
    this.checkout = q.get('checkout') ?? this.checkout;
    const guestsParam = Number(q.get('guests'));
    if (Number.isFinite(guestsParam) && guestsParam > 0) {
      this.guests = guestsParam;
    }

    if (Number.isFinite(roomParam) && roomParam > 0) {
      this.selectedRoomTypeId.set(roomParam);
    }

    if (this.propertyId != null && this.datesValid()) {
      this.searchAvailability();
    }
  }

  protected datesValid(): boolean {
    return !!this.checkin && !!this.checkout && this.nights() >= 1;
  }

  protected searchAvailability(): void {
    this.availError.set(null);
    this.submitError.set(null);

    if (this.propertyId == null) {
      this.availError.set('Please choose a property first.');
      return;
    }
    if (!this.datesValid()) {
      this.availError.set('Check-out must be after check-in.');
      return;
    }

    this.availLoading.set(true);
    this.api
      .checkAvailability({
        property_id: this.propertyId,
        checkin_date: this.checkin,
        checkout_date: this.checkout,
        guests: this.guests,
      })
      .subscribe({
        next: (results) => {
          this.availLoading.set(false);
          this.availability.set(results);
          // Keep a preselected room (from deep link) only if still available.
          const selected = this.selectedRoomTypeId();
          if (selected != null && !results.some((r) => r.room_type_id === selected)) {
            this.selectedRoomTypeId.set(null);
          }
          if (results.length === 0) {
            this.availError.set(null);
          }
        },
        error: (err: unknown) => {
          this.availLoading.set(false);
          this.availability.set(null);
          this.availError.set(err instanceof Error ? err.message : 'Availability check failed.');
        },
      });
  }

  protected selectRoom(result: AvailabilityResult): void {
    this.selectedRoomTypeId.set(result.room_type_id);
    this.submitError.set(null);
  }

  protected submit(): void {
    const result = this.selectedResult();
    if (!result || this.propertyId == null || this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.paymentProcessing.set(false);
    this.submitError.set(null);

    const payload = {
      guest_name: this.guestName.trim(),
      guest_email: this.guestEmail.trim(),
      guest_phone: this.guestPhone.trim(),
      property_id: this.propertyId,
      room_type_id: result.room_type_id,
      checkin_date: this.checkin,
      checkout_date: this.checkout,
      payment_method: this.paymentMethod,
      guests: this.guests,
    };

    this.api.createBooking(payload).subscribe({
      next: (booking) => {
        if (!booking.payment_gateway_url) {
          // No gateway returned — treat the hold as the end state.
          this.confirmation.set({
            booking: { ...booking, payment_method: this.paymentMethod, guest_email: payload.guest_email },
            payment: {
              status: 'success',
              message: 'Booking placed on hold.',
              booking_reference: booking.booking_reference,
              payment_status: 'PENDING',
              state: booking.state,
            },
          });
          this.submitting.set(false);
          return;
        }
        this.paymentProcessing.set(true);
        this.api.processPayment(booking.payment_gateway_url).subscribe({
          next: (payment) => {
            this.submitting.set(false);
            this.confirmation.set({
              booking: { ...booking, payment_method: this.paymentMethod, guest_email: payload.guest_email },
              payment,
            });
          },
          error: (err: unknown) => {
            this.submitting.set(false);
            this.submitError.set(
              (err instanceof Error ? err.message : 'Payment failed.') +
                ' Your booking is on hold — please contact us with reference ' +
                booking.booking_reference +
                '.',
            );
          },
        });
      },
      error: (err: unknown) => {
        this.submitting.set(false);
        this.submitError.set(err instanceof Error ? err.message : 'Could not create the booking.');
      },
    });
  }

  protected methodName(method?: PaymentMethod): string {
    return this.paymentOptions.find((o) => o.id === method)?.name ?? 'selected gateway';
  }

  protected startOver(): void {
    this.confirmation.set(null);
    this.availability.set(null);
    this.selectedRoomTypeId.set(null);
    this.guestName = '';
    this.guestEmail = '';
    this.guestPhone = '';
    this.submitError.set(null);
  }
}

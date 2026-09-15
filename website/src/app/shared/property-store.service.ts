import { Injectable, computed, inject, signal } from '@angular/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { EMPTY } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ApiService } from '../core/api.service';
import { Property, RoomTypeWithProperty } from '../core/models';

/** Shared property catalogue: loaded once, consumed by every page. */
@Injectable({ providedIn: 'root' })
export class PropertyStore {
  private readonly api = inject(ApiService);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly properties = signal<Property[]>([]);

  readonly allRooms = computed<RoomTypeWithProperty[]>(() =>
    this.properties().flatMap((p) =>
      p.room_types.map((r) => ({
        ...r,
        property_id: p.id,
        property_name: p.name,
        property_city: p.city,
      })),
    ),
  );

  constructor() {
    this.refresh();
  }

  refresh(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api
      .getProperties()
      .pipe(
        catchError((err: unknown) => {
          this.error.set(err instanceof Error ? err.message : 'Failed to load properties.');
          this.loading.set(false);
          return EMPTY;
        }),
      )
      .subscribe((props) => {
        this.properties.set(props);
        this.loading.set(false);
      });
  }

  propertyById(id: number): Property | undefined {
    return this.properties().find((p) => p.id === id);
  }

  /** Cold observable of properties — handy for resolver-less routes. */
  readonly properties$ = toObservable(this.properties);
}

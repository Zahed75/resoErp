import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { ConfigService } from './config.service';
import {
  ApiResponse,
  AvailabilityResult,
  BookingCreatePayload,
  BookingCreated,
  PaymentResult,
  Property,
} from './models';

/** Thrown for API-level errors ({status:'error', message}) and transport failures. */
export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
  ) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ConfigService);

  getProperties(): Observable<Property[]> {
    return this.request<Property[]>('GET', '/api/v1/website/properties').pipe(
      map((data) => data ?? []),
    );
  }

  checkAvailability(body: {
    property_id: number;
    checkin_date: string;
    checkout_date: string;
    guests: number;
    room_type_id?: number;
  }): Observable<AvailabilityResult[]> {
    return this.request<AvailabilityResult[]>('POST', '/api/v1/website/availability', body).pipe(
      map((data) => data ?? []),
    );
  }

  createBooking(body: BookingCreatePayload): Observable<BookingCreated> {
    return this.request<BookingCreated>('POST', '/api/v1/website/booking/create', body);
  }

  /** Simulates paying through the gateway URL returned by booking/create. */
  processPayment(gatewayPath: string): Observable<PaymentResult> {
    const path = gatewayPath.startsWith('/') ? gatewayPath : `/${gatewayPath}`;
    return this.request<PaymentResult>('POST', path);
  }

  private request<T>(method: 'GET' | 'POST', path: string, body?: unknown): Observable<T> {
    const url = `${this.config.apiBaseUrl}${path}`;
    const http$ =
      method === 'GET'
        ? this.http.get<ApiResponse<T>>(url)
        : this.http.post<ApiResponse<T>>(url, body ?? {});

    return http$.pipe(
      map((res) => {
        if (res && res.status === 'success') {
          return res.data as T;
        }
        throw new ApiRequestError(
          res && typeof res.message === 'string' ? res.message : 'Unexpected API response.',
          200,
        );
      }),
      catchError((err: unknown) => {
        if (err instanceof ApiRequestError) {
          return throwError(() => err);
        }
        if (err instanceof HttpErrorResponse) {
          let message = `Request failed (${err.status}). Please try again.`;
          const body = err.error as { message?: unknown } | null;
          if (body && typeof body?.message === 'string' && body.message) {
            message = body.message;
          } else if (err.status === 0) {
            message = 'Cannot reach the booking server. Please check your connection.';
          }
          return throwError(() => new ApiRequestError(message, err.status));
        }
        return throwError(() => new ApiRequestError('Something went wrong. Please try again.'));
      }),
    );
  }
}

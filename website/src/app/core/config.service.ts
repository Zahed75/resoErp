import { Injectable } from '@angular/core';

export interface AppConfig {
  /** Base URL of the Odoo API. Empty string = same origin (nginx proxies /api). */
  apiBaseUrl: string;
}

const DEFAULT_CONFIG: AppConfig = { apiBaseUrl: '' };

/**
 * Loads runtime configuration from assets/config.json before the app boots.
 * Falls back to same-origin defaults when the file is missing or malformed.
 */
@Injectable({ providedIn: 'root' })
export class ConfigService {
  private config: AppConfig = DEFAULT_CONFIG;

  get apiBaseUrl(): string {
    return this.config.apiBaseUrl;
  }

  /** APP_INITIALIZER factory. */
  load(): Promise<void> {
    return fetch('config.json')
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`${res.status}`))))
      .then((json: Partial<AppConfig>) => {
        this.config = {
          apiBaseUrl: typeof json.apiBaseUrl === 'string' ? json.apiBaseUrl.replace(/\/$/, '') : '',
        };
      })
      .catch(() => {
        this.config = DEFAULT_CONFIG;
      });
  }
}

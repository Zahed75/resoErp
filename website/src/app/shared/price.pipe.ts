import { Pipe, PipeTransform } from '@angular/core';

/** Formats a price with its currency, e.g. 12500 -> "৳12,500" for BDT. */
@Pipe({ name: 'price', standalone: true })
export class PricePipe implements PipeTransform {
  transform(value: number | null | undefined, currency = ''): string {
    if (value == null || Number.isNaN(value)) {
      return '—';
    }
    const symbol = currency === 'BDT' ? '৳' : '';
    const formatted = new Intl.NumberFormat('en-US', {
      maximumFractionDigits: value % 1 === 0 ? 0 : 2,
    }).format(value);
    return `${symbol}${formatted}${symbol ? '' : ` ${currency}`.trim()}`;
  }
}

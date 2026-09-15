import { AfterViewInit, Directive, ElementRef, OnDestroy, inject, input } from '@angular/core';

/**
 * Scroll-reveal: adds .reveal to the element and toggles .revealed
 * when it enters the viewport (IntersectionObserver).
 * Optional delay input: `appReveal="'120ms'"` for staggered effects.
 */
@Directive({
  selector: '[appReveal]',
})
export class RevealDirective implements AfterViewInit, OnDestroy {
  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef);
  private observer?: IntersectionObserver;

  readonly delay = input('', { alias: 'appReveal' });

  ngAfterViewInit(): void {
    const el = this.el.nativeElement;
    el.classList.add('reveal');
    if (this.delay()) {
      el.style.transitionDelay = this.delay();
    }

    if (typeof IntersectionObserver === 'undefined') {
      el.classList.add('revealed');
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            this.observer?.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' },
    );
    this.observer.observe(el);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }
}

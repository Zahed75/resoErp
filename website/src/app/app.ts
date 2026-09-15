import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { FooterComponent } from './shared/footer.component';
import { NavbarComponent } from './shared/navbar.component';
import { PropertyStore } from './shared/property-store.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, NavbarComponent, FooterComponent],
  template: `
    <div class="app-shell">
      <app-navbar />
      <main class="app-main">
        <router-outlet />
      </main>
      <app-footer [properties]="store.properties()" />
    </div>
  `,
  styles: `
    .app-shell {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }

    .app-main {
      flex: 1;
    }
  `,
})
export class App {
  protected readonly store = inject(PropertyStore);
}

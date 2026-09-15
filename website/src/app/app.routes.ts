import { Routes } from '@angular/router';

import { BookComponent } from './pages/book/book.component';
import { ContactComponent } from './pages/contact/contact.component';
import { HomeComponent } from './pages/home/home.component';
import { NotFoundComponent } from './pages/not-found/not-found.component';
import { RoomDetailComponent } from './pages/room-detail/room-detail.component';
import { RoomsComponent } from './pages/rooms/rooms.component';

export const routes: Routes = [
  { path: '', component: HomeComponent, title: 'Reso Resort — Beach & Forest Retreats' },
  { path: 'rooms', component: RoomsComponent, title: 'Rooms & Villas — Reso Resort' },
  { path: 'rooms/:roomTypeId', component: RoomDetailComponent, title: 'Room — Reso Resort' },
  { path: 'book', component: BookComponent, title: 'Book your stay — Reso Resort' },
  { path: 'contact', component: ContactComponent, title: 'Contact us — Reso Resort' },
  { path: '**', component: NotFoundComponent, title: 'Page not found — Reso Resort' },
];

export interface RoomType {
  id: number;
  name: string;
  max_guests: number;
  bed_type: string;
  base_price: number;
  currency: string;
  amenities: string[];
}

export interface Property {
  id: number;
  name: string;
  code: string;
  city: string;
  phone: string;
  email: string;
  checkin_time: string;
  checkout_time: string;
  room_types: RoomType[];
}

export interface AvailabilityResult {
  room_type_id: number;
  name: string;
  available_count: number;
  price_per_night: number;
  total_price: number;
  currency: string;
}

export type PaymentMethod = 'bkash' | 'nagad' | 'sslcommerz' | 'stripe';

export interface BookingCreatePayload {
  guest_name: string;
  guest_email: string;
  guest_phone: string;
  property_id: number;
  room_type_id: number;
  checkin_date: string;
  checkout_date: string;
  payment_method: PaymentMethod;
  guests: number;
}

export interface BookingCreated {
  booking_reference: string;
  guest_name: string;
  amount_total: number;
  currency: string;
  state: string;
  payment_gateway_url?: string;
}

export interface PaymentResult {
  status: string;
  message: string;
  booking_reference: string;
  payment_status: string;
  state: string;
}

export interface ApiSuccess<T> {
  status: 'success';
  data: T;
}

export interface ApiError {
  status: 'error';
  message: string;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

/** A room type paired with the property it belongs to (for cross-property listings). */
export interface RoomTypeWithProperty extends RoomType {
  property_id: number;
  property_name: string;
  property_city: string;
}

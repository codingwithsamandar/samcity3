import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'token_storage.dart';
import 'deep_link_service.dart';
import 'auth/auth_repository.dart';
import 'auth/user.dart';
import '../features/ads/ads_repository.dart';
import '../features/delivery/delivery_repository.dart';
import '../features/delivery/delivery_models.dart';
import '../features/taxi/taxi_repository.dart';
import '../features/chat/chat_repository.dart';
import '../features/booking/booking_repository.dart';
import '../features/notifications/notifications_repository.dart';
import '../features/payments/payment_repository.dart';
import '../features/places/places_repository.dart';
import '../features/community/community_repository.dart';
import '../features/jobs/jobs_repository.dart';
import '../features/services/services_repository.dart';

// ─── Infratuzilma ─────────────────────────────────────────────────────────────
final tokenStorageProvider = Provider((ref) => TokenStorage());
final deepLinkServiceProvider = Provider((ref) {
  final service = DeepLinkService();
  service.start();
  ref.onDispose(service.dispose);
  return service;
});
final apiClientProvider =
    Provider((ref) => ApiClient(ref.read(tokenStorageProvider)));

// ─── Repozitoriylar ───────────────────────────────────────────────────────────
final authRepositoryProvider = Provider((ref) => AuthRepository(
      ref.read(apiClientProvider),
      ref.read(tokenStorageProvider),
    ));
final adsRepositoryProvider =
    Provider((ref) => AdsRepository(ref.read(apiClientProvider)));
final deliveryRepositoryProvider =
    Provider((ref) => DeliveryRepository(ref.read(apiClientProvider)));
final taxiRepositoryProvider =
    Provider((ref) => TaxiRepository(ref.read(apiClientProvider)));
final chatRepositoryProvider =
    Provider((ref) => ChatRepository(ref.read(apiClientProvider)));
final bookingRepositoryProvider =
    Provider((ref) => BookingRepository(ref.read(apiClientProvider)));
final notificationsRepositoryProvider =
    Provider((ref) => NotificationsRepository(ref.read(apiClientProvider)));
final paymentRepositoryProvider =
    Provider((ref) => PaymentRepository(ref.read(apiClientProvider)));
final placesRepositoryProvider =
    Provider((ref) => PlacesRepository(ref.read(apiClientProvider)));
final communityRepositoryProvider =
    Provider((ref) => CommunityRepository(ref.read(apiClientProvider)));
final jobsRepositoryProvider =
    Provider((ref) => JobsRepository(ref.read(apiClientProvider)));
final servicesRepositoryProvider =
    Provider((ref) => ServicesRepository(ref.read(apiClientProvider)));

// ─── Savat holati (badge + checkout uchun) ────────────────────────────────────
class CartController extends StateNotifier<Cart> {
  CartController(this._repo) : super(Cart.empty());
  final DeliveryRepository _repo;

  Future<void> refresh() async {
    try {
      state = await _repo.cart();
    } catch (_) {/* login bo'lmasa bo'sh qoladi */}
  }

  Future<void> add(String productId, {int quantity = 1}) async =>
      state = await _repo.add(productId, quantity: quantity);
  Future<void> setQty(String productId, int qty) async =>
      state = await _repo.setQty(productId, qty);
  Future<void> remove(String productId) async =>
      state = await _repo.remove(productId);
  void clearLocal() => state = Cart.empty();
}

final cartControllerProvider =
    StateNotifierProvider<CartController, Cart>(
        (ref) => CartController(ref.read(deliveryRepositoryProvider)));

// ─── Bildirishnoma o'qilmaganlar soni (qo'ng'iroq badge'i) ────────────────────
class NotifController extends StateNotifier<int> {
  NotifController(this._repo) : super(0);
  final NotificationsRepository _repo;

  Future<void> refresh() async {
    try {
      state = await _repo.unreadCount();
    } catch (_) {/* login bo'lmasa 0 qoladi */}
  }

  /// WebSocket'dan kelgan jonli sonni o'rnatadi.
  void setCount(int count) => state = count;

  void reset() => state = 0;
}

final notifControllerProvider =
    StateNotifierProvider<NotifController, int>(
        (ref) => NotifController(ref.read(notificationsRepositoryProvider)));

// ─── Auth holati ──────────────────────────────────────────────────────────────
class AuthState {
  final bool loading;
  final AppUser? user;
  const AuthState({this.loading = true, this.user});

  bool get isAuthenticated => user != null;
  AuthState copyWith({bool? loading, AppUser? user}) =>
      AuthState(loading: loading ?? this.loading, user: user ?? this.user);
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(this._repo) : super(const AuthState()) {
    _bootstrap();
  }
  final AuthRepository _repo;

  Future<void> _bootstrap() async {
    if (await _repo.hasSession()) {
      try {
        final user = await _repo.me();
        state = AuthState(loading: false, user: user);
        return;
      } catch (_) {
        await _repo.logout();
      }
    }
    state = const AuthState(loading: false);
  }

  void setUser(AppUser user) => state = AuthState(loading: false, user: user);

  Future<void> logout() async {
    await _repo.logout();
    state = const AuthState(loading: false);
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>(
        (ref) => AuthController(ref.read(authRepositoryProvider)));

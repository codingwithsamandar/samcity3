import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'providers.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/otp_screen.dart';
import '../features/ads/ad_detail_screen.dart';
import '../features/ads/add_ad_screen.dart';
import '../features/delivery/store_detail_screen.dart';
import '../features/taxi/taxist_detail_screen.dart';
import '../features/taxi/my_trips_screen.dart';
import '../features/delivery/cart_screen.dart';
import '../features/delivery/my_orders_screen.dart';
import '../features/delivery/my_stores_screen.dart';
import '../features/chat/chat_room_screen.dart';
import '../features/booking/venues_screen.dart';
import '../features/booking/venue_detail_screen.dart';
import '../features/booking/venue_book_screen.dart';
import '../features/booking/my_bookings_screen.dart';
import '../features/profile/profile_edit_screen.dart';
import '../features/notifications/notifications_screen.dart';
import '../features/places/places_map_screen.dart';
import '../features/community/community_screen.dart';
import '../features/jobs/jobs_screen.dart';
import '../features/services/services_screen.dart';
import '../features/shell/home_shell.dart';

/// Ilova marshrutlari. Auth holatiga qarab kirish/asosiy ekranga yo'naltiradi.
final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authControllerProvider);

  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      if (auth.loading) return null;
      final loggingIn = state.matchedLocation == '/login' ||
          state.matchedLocation == '/otp';
      if (!auth.isAuthenticated && !loggingIn) return '/login';
      if (auth.isAuthenticated && loggingIn) return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => const HomeShell()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/otp',
        builder: (_, st) => OtpScreen(phone: st.extra as String? ?? ''),
      ),
      GoRoute(path: '/ad-new', builder: (_, __) => const AddAdScreen()),
      GoRoute(
        path: '/ad/:id',
        builder: (_, st) => AdDetailScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(
        path: '/store/:id',
        builder: (_, st) => StoreDetailScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(
        path: '/taxist/:id',
        builder: (_, st) => TaxistDetailScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(path: '/trips', builder: (_, __) => const MyTripsScreen()),
      GoRoute(path: '/cart', builder: (_, __) => const CartScreen()),
      GoRoute(path: '/orders', builder: (_, __) => const MyOrdersScreen()),
      GoRoute(path: '/my-stores', builder: (_, __) => const MyStoresScreen()),
      GoRoute(path: '/venues', builder: (_, __) => const VenuesScreen()),
      GoRoute(
        path: '/venue/:id',
        builder: (_, st) => VenueDetailScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(
        path: '/venue-book/:id',
        builder: (_, st) => VenueBookScreen(id: st.pathParameters['id']!),
      ),
      GoRoute(path: '/my-bookings', builder: (_, __) => const MyBookingsScreen()),
      GoRoute(path: '/notifications', builder: (_, __) => const NotificationsScreen()),
      GoRoute(path: '/map', builder: (_, __) => const PlacesMapScreen()),
      GoRoute(path: '/community', builder: (_, __) => const CommunityScreen()),
      GoRoute(path: '/jobs', builder: (_, __) => const JobsScreen()),
      GoRoute(path: '/service-payments', builder: (_, __) => const ServicesScreen()),
      GoRoute(path: '/profile-edit', builder: (_, __) => const ProfileEditScreen()),
      GoRoute(
        path: '/chat/:id',
        builder: (_, st) => ChatRoomScreen(
          roomId: st.pathParameters['id']!,
          title: st.extra as String? ?? 'Chat',
        ),
      ),
    ],
  );
});

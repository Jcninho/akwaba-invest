import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/alerts/presentation/alerts_screen.dart';
import '../../features/auth/domain/providers/auth_provider.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/screens/register_screen.dart';
import '../../features/market/presentation/screens/market_screen.dart';
import '../../features/stock_detail/presentation/stock_detail_screen.dart';
import '../../features/portfolio/presentation/screens/portfolio_screen.dart';
import '../../features/profile/presentation/screens/profile_screen.dart';
import '../../features/simulator/presentation/simulator_screen.dart';
import '../../shared/widgets/akwaba_scaffold.dart';

/// Riverpod provider for the application [GoRouter].
///
/// Watches [authProvider] so that the router is recreated — and the [redirect]
/// callback re-evaluated — whenever the authentication state changes.
///
/// Redirect logic:
///   - Not logged-in + non-auth route  → /login
///   - Logged-in    + auth route       → /market
///   - Otherwise                       → no redirect (null)
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/market',
    debugLogDiagnostics: false,
    redirect: (context, state) {
      // valueOrNull is null when state is AsyncLoading or AsyncError.
      final isLoggedIn = authState.valueOrNull != null;
      final isAuthRoute = state.matchedLocation == '/login' ||
          state.matchedLocation == '/register';

      if (!isLoggedIn && !isAuthRoute) return '/login';
      if (isLoggedIn && isAuthRoute) return '/market';
      return null;
    },
    routes: [
      // ── Auth routes (no bottom nav) ──────────────────────────────────────
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (_, __) => const RegisterScreen(),
      ),

      // ── Full-screen stock detail (outside bottom-nav shell) ──────────────
      GoRoute(
        path: '/stock/:symbol',
        builder: (_, state) => StockDetailScreen(
          // safe: path parameter is always present when this route matches
          symbol: state.pathParameters['symbol']!,
        ),
      ),

      // ── Shell with bottom navigation bar (5 tabs) ────────────────────────
      ShellRoute(
        builder: (context, state, child) => AkwabaScaffold(child: child),
        routes: [
          GoRoute(
            path: '/market',
            builder: (_, __) => const MarketScreen(),
          ),
          GoRoute(
            path: '/portfolio',
            builder: (_, __) => const PortfolioScreen(),
          ),
          GoRoute(
            path: '/alerts',
            builder: (_, __) => const AlertsScreen(),
          ),
          GoRoute(
            path: '/simulator',
            builder: (_, __) => const SimulatorScreen(),
          ),
          GoRoute(
            path: '/profile',
            builder: (_, __) => const ProfileScreen(),
          ),
        ],
      ),
    ],
  );
});

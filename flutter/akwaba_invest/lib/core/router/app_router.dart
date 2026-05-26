import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/alerts/presentation/screens/alerts_screen.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/market/presentation/screens/market_screen.dart';
import '../../features/market/presentation/screens/stock_detail_screen.dart';
import '../../features/portfolio/presentation/screens/portfolio_screen.dart';
import '../../features/profile/presentation/screens/profile_screen.dart';
import '../../features/simulator/presentation/screens/simulator_screen.dart';

/// Application router.
///
/// Redirect logic:
///   /  → /login (placeholder; TODO: redirect to /market when authenticated)
///
/// Shell route wraps the 5-tab bottom navigation:
///   Market | Portfolio | Alertes | Simulateur | Profil
final appRouter = GoRouter(
  initialLocation: '/login',
  debugLogDiagnostics: false,
  routes: [
    // Root redirect
    GoRoute(
      path: '/',
      redirect: (_, __) => '/login',
      // TODO: redirect to '/market' when authStateProvider returns true
    ),

    // Auth
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),

    // Full-screen stock detail (outside bottom nav shell)
    GoRoute(
      path: '/stock/:symbol',
      builder: (context, state) => StockDetailScreen(
        symbol: state.pathParameters['symbol'] ?? '',
      ),
    ),

    // Shell with bottom navigation bar (5 tabs)
    StatefulShellRoute.indexedStack(
      builder: (context, state, navigationShell) =>
          _ShellScaffold(navigationShell: navigationShell),
      branches: [
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/market',
              builder: (context, state) => const MarketScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/portfolio',
              builder: (context, state) => const PortfolioScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/alerts',
              builder: (context, state) => const AlertsScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/simulator',
              builder: (context, state) => const SimulatorScreen(),
            ),
          ],
        ),
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/profile',
              builder: (context, state) => const ProfileScreen(),
            ),
          ],
        ),
      ],
    ),
  ],
);

/// Bottom navigation scaffold shared by all shell branches.
class _ShellScaffold extends StatelessWidget {
  const _ShellScaffold({required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (index) => navigationShell.goBranch(
          index,
          initialLocation: index == navigationShell.currentIndex,
        ),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.show_chart),
            label: 'Marché',
          ),
          NavigationDestination(
            icon: Icon(Icons.pie_chart_outline),
            selectedIcon: Icon(Icons.pie_chart),
            label: 'Portefeuille',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined),
            selectedIcon: Icon(Icons.notifications),
            label: 'Alertes',
          ),
          NavigationDestination(
            icon: Icon(Icons.calculate),
            label: 'Simulateur',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profil',
          ),
        ],
      ),
    );
  }
}

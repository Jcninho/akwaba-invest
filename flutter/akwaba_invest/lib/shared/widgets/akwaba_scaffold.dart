import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';

/// Main application scaffold with a bottom navigation bar (5 tabs).
///
/// Wrapped by the [ShellRoute] in [app_router.dart]; receives the current
/// branch's [child] widget and renders it inside the scaffold body.
///
/// Tab → route mapping:
///   0 Marché       → /market
///   1 Portefeuille → /portfolio
///   2 Alertes      → /alerts
///   3 Simulateur   → /simulator
///   4 Profil       → /profile
class AkwabaScaffold extends StatefulWidget {
  const AkwabaScaffold({super.key, required this.child});

  final Widget child;

  @override
  State<AkwabaScaffold> createState() => _AkwabaScaffoldState();
}

class _AkwabaScaffoldState extends State<AkwabaScaffold> {
  static const List<String> _tabRoutes = [
    '/market',
    '/portfolio',
    '/alerts',
    '/simulator',
    '/profile',
  ];

  /// Derives the selected tab index from the current route location.
  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    for (int i = 0; i < _tabRoutes.length; i++) {
      if (location.startsWith(_tabRoutes[i])) return i;
    }
    return 0; // default to Marché
  }

  void _onTabTapped(BuildContext context, int index) {
    context.go(_tabRoutes[index]);
  }

  @override
  Widget build(BuildContext context) {
    final currentIndex = _currentIndex(context);

    return Scaffold(
      body: widget.child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) => _onTabTapped(context, index),
        backgroundColor: AppColors.white,
        indicatorColor: AppColors.greenLight,
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
            icon: Icon(Icons.calculate_outlined),
            selectedIcon: Icon(Icons.calculate),
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

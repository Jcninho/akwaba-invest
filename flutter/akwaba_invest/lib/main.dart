import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase is required for Auth and FCM push notifications.
  // In development the google-services.json may be absent → catch gracefully.
  try {
    await Firebase.initializeApp();
  } catch (e) {
    debugPrint('Firebase.initializeApp skipped (dev environment): $e');
  }

  runApp(const ProviderScope(child: AkwabaApp()));
}

/// Root widget. Watches [routerProvider] so that the router (and its auth
/// guard) rebuilds whenever the authentication state changes.
class AkwabaApp extends ConsumerWidget {
  const AkwabaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'Akwaba Invest',
      theme: AppTheme.light(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}

import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../core/constants/app_constants.dart';
import '../data/portfolio_repository.dart';
import 'models/portfolio_model.dart';

// ---------------------------------------------------------------------------
// Repository provider
// ---------------------------------------------------------------------------

final portfolioRepositoryProvider = Provider<PortfolioRepository>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: '${AppConstants.apiBaseUrl}${AppConstants.apiVersion}',
      connectTimeout:
          const Duration(milliseconds: AppConstants.connectTimeout),
      receiveTimeout:
          const Duration(milliseconds: AppConstants.receiveTimeout),
      headers: const {'Content-Type': 'application/json'},
    ),
  );

  // Attach a fresh Firebase Bearer token to every portfolio request.
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        try {
          final user = FirebaseAuth.instance.currentUser;
          if (user != null) {
            final token = await user.getIdToken(true); // force refresh
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
              const storage = FlutterSecureStorage();
              await storage.write(key: 'firebase_token', value: token);
            }
          }
        } catch (_) {
          // Fallback to stored token when network is unavailable.
          const storage = FlutterSecureStorage();
          final token = await storage.read(key: 'firebase_token');
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        handler.next(options);
      },
    ),
  );

  return PortfolioRepository(dio);
});

// ---------------------------------------------------------------------------
// Portfolio notifier + provider
// ---------------------------------------------------------------------------

final portfolioProvider =
    AsyncNotifierProvider<PortfolioNotifier, PortfolioModel?>(
  PortfolioNotifier.new,
);

class PortfolioNotifier extends AsyncNotifier<PortfolioModel?> {
  @override
  Future<PortfolioModel?> build() async {
    try {
      return await ref.read(portfolioRepositoryProvider).getPortfolio();
    } catch (_) {
      return null;
    }
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(portfolioRepositoryProvider).getPortfolio(),
    );
  }

  Future<void> addLine(String symbol, double quantity, double price) async {
    final result = await ref
        .read(portfolioRepositoryProvider)
        .addLine(symbol, quantity, price);
    state = AsyncData(result);
  }

  Future<void> removeLine(int lineId) async {
    final result =
        await ref.read(portfolioRepositoryProvider).removeLine(lineId);
    state = AsyncData(result);
  }
}

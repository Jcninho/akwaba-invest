import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../../core/constants/app_constants.dart';
import '../../data/alerts_repository.dart';
import '../models/alert_model.dart';

final alertsRepositoryProvider = Provider<AlertsRepository>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: '${AppConstants.apiBaseUrl}${AppConstants.apiVersion}',
      connectTimeout: const Duration(milliseconds: AppConstants.connectTimeout),
      receiveTimeout: const Duration(milliseconds: AppConstants.receiveTimeout),
      headers: const {'Content-Type': 'application/json'},
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        try {
          final user = FirebaseAuth.instance.currentUser;
          if (user != null) {
            final token = await user.getIdToken(true);
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
              const storage = FlutterSecureStorage();
              await storage.write(key: 'firebase_token', value: token);
            }
          }
        } catch (_) {
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

  return AlertsRepository(dio);
});

final alertsProvider =
    AsyncNotifierProvider<AlertsNotifier, List<AlertModel>>(AlertsNotifier.new);

class AlertsNotifier extends AsyncNotifier<List<AlertModel>> {
  @override
  Future<List<AlertModel>> build() async {
    return ref.read(alertsRepositoryProvider).getAlerts();
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(alertsRepositoryProvider).getAlerts(),
    );
  }

  Future<void> createAlert({
    required String symbol,
    required String alertType,
    double? threshold,
  }) async {
    final alert = await ref.read(alertsRepositoryProvider).createAlert(
          symbol: symbol,
          alertType: alertType,
          threshold: threshold,
        );
    state = AsyncData([...?state.valueOrNull, alert]);
  }

  Future<void> deleteAlert(int alertId) async {
    await ref.read(alertsRepositoryProvider).deleteAlert(alertId);
    state = AsyncData(
      (state.valueOrNull ?? []).where((a) => a.id != alertId).toList(),
    );
  }

  Future<void> toggleAlert(int alertId, {required bool isActive}) async {
    final updated = await ref
        .read(alertsRepositoryProvider)
        .toggleAlert(alertId, isActive: isActive);
    state = AsyncData(
      (state.valueOrNull ?? [])
          .map((a) => a.id == alertId ? updated : a)
          .toList(),
    );
  }
}

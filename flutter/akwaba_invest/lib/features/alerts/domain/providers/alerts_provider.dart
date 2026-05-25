import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/alerts_repository.dart';

final alertsRepositoryProvider = Provider<AlertsRepository>((ref) {
  // TODO: replace Dio() with DioClient.getInstance() via FutureProvider
  return AlertsRepository(Dio());
});

/// All alerts for the authenticated user.
final alertsProvider =
    AsyncNotifierProvider<AlertsNotifier, List<dynamic>>(AlertsNotifier.new);

class AlertsNotifier extends AsyncNotifier<List<dynamic>> {
  @override
  Future<List<dynamic>> build() async {
    // TODO: call ref.read(alertsRepositoryProvider).getAlerts()
    return [];
  }

  Future<void> createAlert({
    required String symbol,
    required String alertType,
    double? threshold,
  }) async {
    // TODO: call repository.createAlert() and refresh state
  }

  Future<void> deleteAlert(int alertId) async {
    // TODO: call repository.deleteAlert(alertId) and refresh state
  }

  Future<void> toggleAlert(int alertId, {required bool isActive}) async {
    // TODO: call repository.toggleAlert() and refresh state
  }
}

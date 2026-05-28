import 'package:dio/dio.dart';

import '../domain/models/alert_model.dart';

class AlertsRepository {
  final Dio _dio;

  AlertsRepository(this._dio);

  Future<List<AlertModel>> getAlerts() async {
    final response = await _dio.get<List<dynamic>>('/alerts/');
    return (response.data ?? [])
        .map((e) => AlertModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<AlertModel> createAlert({
    required String symbol,
    required String alertType,
    double? threshold,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/alerts/',
      data: {
        'symbol': symbol,
        'alert_type': alertType,
        if (threshold != null) 'threshold': threshold,
      },
    );
    return AlertModel.fromJson(response.data!);
  }

  Future<void> deleteAlert(int alertId) async {
    await _dio.delete<void>('/alerts/$alertId');
  }

  Future<AlertModel> toggleAlert(int alertId, {required bool isActive}) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/alerts/$alertId/toggle',
      data: {'is_active': isActive},
    );
    return AlertModel.fromJson(response.data!);
  }
}

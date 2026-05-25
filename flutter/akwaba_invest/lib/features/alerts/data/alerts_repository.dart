import 'package:dio/dio.dart';

class AlertsRepository {
  final Dio _dio;

  AlertsRepository(this._dio);

  Dio get client => _dio;

  // TODO: GET    /alerts/              → List<AlertRead>
  // TODO: POST   /alerts/              → AlertRead (create alert)
  // TODO: DELETE /alerts/{id}          → 204
  // TODO: PATCH  /alerts/{id}/toggle   → AlertRead
}

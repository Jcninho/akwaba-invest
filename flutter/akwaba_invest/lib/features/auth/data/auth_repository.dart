import 'package:dio/dio.dart';

class AuthRepository {
  final Dio _dio;

  AuthRepository(this._dio);

  Dio get client => _dio;

  // TODO: verify Firebase ID token with backend → returns UserRead
  // TODO: sign out (clear secure storage token)
  // TODO: refresh Firebase token and persist to secure storage
}

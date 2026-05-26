import 'dart:developer' as developer;

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/app_constants.dart';

/// Dio singleton with:
///   - BaseUrl from AppConstants
///   - Auth interceptor: reads Firebase token from secure storage
///   - Error interceptor: logs 401 / 403 / 500 responses
///
/// Use [getInstance] to get a fully-configured [Dio] instance.
class DioClient {
  static const String _tokenKey = 'firebase_token';
  static final _storage = FlutterSecureStorage();

  static Future<Dio> getInstance() async {
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

    dio.interceptors
      ..add(_AuthInterceptor(_storage, _tokenKey))
      ..add(_ErrorInterceptor());

    return dio;
  }
}

/// Adds "Authorization: Bearer {token}" to every request.
class _AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _storage;
  final String _tokenKey;

  _AuthInterceptor(this._storage, this._tokenKey);

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.read(key: _tokenKey);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

/// Logs HTTP errors and handles auth/premium redirects.
class _ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    switch (err.response?.statusCode) {
      case 401:
        developer.log(
          'Token expired — redirect to /login',
          name: 'DioClient',
        );
        // TODO: clear token via flutter_secure_storage and navigate to /login
        break;
      case 403:
        developer.log('Premium required', name: 'DioClient');
        break;
      case 500:
        developer.log(
          'Server error: ${err.message}',
          name: 'DioClient',
        );
        break;
    }
    handler.next(err);
  }
}

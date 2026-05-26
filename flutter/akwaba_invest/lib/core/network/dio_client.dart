import 'dart:developer' as developer;

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../constants/app_constants.dart';

/// Singleton [Dio] factory with:
///   - BaseUrl from [AppConstants]
///   - Auth interceptor: injects "Authorization: Bearer {token}" from secure
///     storage on every request
///   - Error interceptor: logs 401 / 403 / 500 responses
///
/// Use [getInstance] for the shared singleton (features, repositories).
/// Use [createBasic] for contexts that manage auth headers manually
/// (e.g. [AuthRepository]).
class DioClient {
  static Dio? _instance;
  static const String _tokenKey = 'firebase_token';

  DioClient._();

  // ---------------------------------------------------------------------------
  // Public factory methods
  // ---------------------------------------------------------------------------

  /// Returns (or lazily creates) the shared singleton [Dio] instance.
  ///
  /// The instance is configured with the auth interceptor that reads the
  /// Firebase ID token from secure storage on every outbound request.
  static Future<Dio> getInstance() async {
    if (_instance != null) return _instance!;

    final storage = const FlutterSecureStorage();

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
      ..add(_AuthInterceptor(storage, _tokenKey))
      ..add(_ErrorInterceptor());

    _instance = dio;
    return _instance!;
  }

  /// Creates a plain [Dio] instance **without** the auth interceptor.
  ///
  /// Intended for [AuthRepository], which manages Authorization headers
  /// directly to avoid a circular dependency with token retrieval.
  static Dio createBasic() {
    return Dio(
      BaseOptions(
        baseUrl: '${AppConstants.apiBaseUrl}${AppConstants.apiVersion}',
        connectTimeout:
            const Duration(milliseconds: AppConstants.connectTimeout),
        receiveTimeout:
            const Duration(milliseconds: AppConstants.receiveTimeout),
        headers: const {'Content-Type': 'application/json'},
      ),
    );
  }

  /// Clears the singleton — used in tests to get a fresh instance.
  static void reset() => _instance = null;
}

// ---------------------------------------------------------------------------
// Interceptors
// ---------------------------------------------------------------------------

/// Injects "Authorization: Bearer {token}" into every request.
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

/// Logs HTTP error responses and handles auth / premium error codes.
class _ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    switch (err.response?.statusCode) {
      case 401:
        developer.log(
          'Token expired — redirect to /login required',
          name: 'DioClient',
        );
        // TODO(P3-03): clear token via flutter_secure_storage and navigate
        // to /login using a global navigator key.
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

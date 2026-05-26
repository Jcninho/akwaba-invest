import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_constants.dart';
import '../../data/auth_repository.dart';
import '../models/app_user.dart';

// ---------------------------------------------------------------------------
// Repository provider
// ---------------------------------------------------------------------------

/// Provides an [AuthRepository] backed by a simple [Dio] instance.
///
/// The auth repository manages its own Authorization headers directly, so it
/// does not use the singleton [DioClient] (which would cause a circular
/// dependency: DioClient reads the token → token comes from auth → auth needs
/// Dio).
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: '${AppConstants.apiBaseUrl}${AppConstants.apiVersion}',
      connectTimeout: const Duration(milliseconds: AppConstants.connectTimeout),
      receiveTimeout: const Duration(milliseconds: AppConstants.receiveTimeout),
      headers: const {'Content-Type': 'application/json'},
    ),
  );
  return AuthRepository(dio);
});

// ---------------------------------------------------------------------------
// Auth state provider
// ---------------------------------------------------------------------------

/// Main authentication state provider.
///
/// State:
///   - [AsyncLoading] — initial check or sign-in in progress
///   - [AsyncData<AppUser>] — user is authenticated
///   - [AsyncData<null>] — user is not authenticated
///   - [AsyncError] — authentication failed
final authProvider = AsyncNotifierProvider<AuthNotifier, AppUser?>(
  AuthNotifier.new,
);

class AuthNotifier extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    // Check whether a Firebase user is already logged in on startup.
    return ref.read(authRepositoryProvider).getCurrentUser();
  }

  /// Signs in with email and password.
  Future<void> signInWithEmail(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(authRepositoryProvider)
          .signInWithEmail(email, password),
    );
  }

  /// Starts the Google Sign-In flow.
  Future<void> signInWithGoogle() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(authRepositoryProvider).signInWithGoogle(),
    );
  }

  /// Creates a new account with email and password.
  Future<void> register(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(authRepositoryProvider)
          .registerWithEmail(email, password),
    );
  }

  /// Signs out and resets state to null (not authenticated).
  Future<void> signOut() async {
    await ref.read(authRepositoryProvider).signOut();
    state = const AsyncData(null);
  }
}

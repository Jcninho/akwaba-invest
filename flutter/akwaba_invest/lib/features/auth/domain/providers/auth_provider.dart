import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/auth_repository.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  // TODO: replace Dio() with DioClient.getInstance() via FutureProvider
  return AuthRepository(Dio());
});

/// Whether the user is currently authenticated.
/// TODO: derive from Firebase Auth stream once wired up.
final authStateProvider =
    AsyncNotifierProvider<AuthNotifier, bool>(AuthNotifier.new);

class AuthNotifier extends AsyncNotifier<bool> {
  @override
  Future<bool> build() async {
    // TODO: check firebase_auth currentUser / secure storage token
    return false;
  }

  Future<void> signOut() async {
    // TODO: clear secure storage, sign out from Firebase
    state = const AsyncData(false);
  }
}

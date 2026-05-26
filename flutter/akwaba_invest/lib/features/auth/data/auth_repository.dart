import 'dart:developer' as developer;

import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../domain/models/app_user.dart';

/// Handles all Firebase Auth operations and backend user synchronisation.
///
/// Flow for every sign-in / register / session restore:
///   1. Authenticate with Firebase (email/password, Google, or existing session)
///   2. Persist the Firebase ID token in [FlutterSecureStorage]
///   3. POST /auth/register   — idempotent upsert; creates the row if absent
///   4. GET  /auth/me         — fetch the user plan from the backend DB
///   5. Return [AppUser]; fallback to plan:'free' on any network failure
class AuthRepository {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final Dio _dio;

  static const String _tokenKey = 'firebase_token';

  AuthRepository(this._dio);

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /// Signs in with [email] and [password].
  Future<AppUser> signInWithEmail(String email, String password) async {
    final credential = await _auth.signInWithEmailAndPassword(
      email: email,
      password: password,
    );
    final user = credential.user;
    if (user == null) throw Exception('Sign-in failed: no user returned.');
    return _registerAndFetchUser(user);
  }

  /// Creates a new account with [email] and [password].
  Future<AppUser> registerWithEmail(String email, String password) async {
    final credential = await _auth.createUserWithEmailAndPassword(
      email: email,
      password: password,
    );
    final user = credential.user;
    if (user == null) throw Exception('Registration failed: no user returned.');
    return _registerAndFetchUser(user);
  }

  /// Initiates a Google Sign-In flow.
  ///
  /// Throws if the user cancels the flow.
  Future<AppUser> signInWithGoogle() async {
    final googleAccount = await _googleSignIn.signIn();
    if (googleAccount == null) throw Exception('Google sign-in cancelled.');

    final googleAuth = await googleAccount.authentication;
    final credential = GoogleAuthProvider.credential(
      accessToken: googleAuth.accessToken,
      idToken: googleAuth.idToken,
    );

    final userCredential = await _auth.signInWithCredential(credential);
    final user = userCredential.user;
    if (user == null) {
      throw Exception('Google sign-in failed: no user returned.');
    }
    return _registerAndFetchUser(user);
  }

  /// Signs out from Firebase and Google, then clears stored credentials.
  Future<void> signOut() async {
    await Future.wait([
      _auth.signOut(),
      _googleSignIn.signOut(),
    ]);
    await _storage.delete(key: _tokenKey);
  }

  /// Returns a fresh Firebase ID token, falling back to the stored one.
  ///
  /// Returns `null` when no user is authenticated.
  Future<String?> getToken() async {
    final currentUser = _auth.currentUser;
    if (currentUser != null) {
      try {
        // Force-refresh to get a non-expired token.
        final freshToken = await currentUser.getIdToken(true);
        await _persistToken(freshToken);
        return freshToken;
      } catch (e) {
        developer.log(
          'Token refresh failed, falling back to stored token: $e',
          name: 'AuthRepository',
        );
      }
    }
    return _storage.read(key: _tokenKey);
  }

  /// Returns the currently authenticated [AppUser].
  ///
  /// Calls POST /auth/register (idempotent) then GET /auth/me so that a user
  /// who authenticated on a previous session is always registered in the DB
  /// before the plan is fetched.
  ///
  /// Returns `null` when no Firebase user is logged in.
  Future<AppUser?> getCurrentUser() async {
    final firebaseUser = _auth.currentUser;
    if (firebaseUser == null) return null;
    return _registerAndFetchUser(firebaseUser);
  }

  /// Stream of raw Firebase [User] auth-state changes.
  ///
  /// Emits `null` when the user signs out.
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /// Core auth/sync flow shared by all sign-in paths and session restores.
  ///
  /// Steps:
  ///   1. Get (and persist) a fresh Firebase ID token.
  ///   2. POST /auth/register — idempotent upsert; safe on every call.
  ///   3. GET  /auth/me       — returns the user row with the current plan.
  ///   4. On any network error: return a valid [AppUser] with plan:'free'
  ///      so that offline / first-boot scenarios never block the user.
  Future<AppUser> _registerAndFetchUser(User firebaseUser) async {
    final token = await firebaseUser.getIdToken();
    await _persistToken(token);

    final authOptions = Options(
      headers: {'Authorization': 'Bearer $token'},
    );

    try {
      // Step 1: Upsert the user row in the backend DB.
      // This is idempotent — safe to call on every sign-in.
      await _dio.post('/auth/register', options: authOptions);

      // Step 2: Fetch the user's plan from the backend.
      final meResponse = await _dio.get('/auth/me', options: authOptions);
      final data = meResponse.data as Map<String, dynamic>;

      return AppUser(
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? '',
        displayName: firebaseUser.displayName,
        plan: data['plan'] as String? ?? 'free',
      );
    } catch (e) {
      developer.log(
        'Auth API call failed, returning user with free plan: $e',
        name: 'AuthRepository',
      );
      // Offline or server error — return a usable AppUser so the app
      // continues to function. Plan will be re-fetched on next launch.
      return AppUser(
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? '',
        displayName: firebaseUser.displayName,
      );
    }
  }

  Future<void> _persistToken(String? token) async {
    if (token != null) {
      await _storage.write(key: _tokenKey, value: token);
    }
  }
}

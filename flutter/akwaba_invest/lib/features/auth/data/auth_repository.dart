import 'dart:developer' as developer;

import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../domain/models/app_user.dart';

/// Handles all Firebase Auth operations and backend user synchronisation.
///
/// This repository:
///  - delegates authentication to [FirebaseAuth] / [GoogleSignIn]
///  - stores the Firebase ID token in [FlutterSecureStorage]
///  - upserts the user in the backend via POST /auth/register
///  - fetches the user plan via GET /auth/me
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
  ///
  /// Persists the ID token and upserts the user in the backend.
  Future<AppUser> signInWithEmail(String email, String password) async {
    final credential = await _auth.signInWithEmailAndPassword(
      email: email,
      password: password,
    );
    final user = credential.user;
    if (user == null) throw Exception('Sign-in failed: no user returned.');
    final token = await user.getIdToken();
    await _persistToken(token);
    return _upsertUser(user, token);
  }

  /// Creates a new account with [email] and [password].
  ///
  /// Persists the ID token and upserts the user in the backend.
  Future<AppUser> registerWithEmail(String email, String password) async {
    final credential = await _auth.createUserWithEmailAndPassword(
      email: email,
      password: password,
    );
    final user = credential.user;
    if (user == null) throw Exception('Registration failed: no user returned.');
    final token = await user.getIdToken();
    await _persistToken(token);
    return _upsertUser(user, token);
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
    if (user == null) throw Exception('Google sign-in failed: no user returned.');

    final token = await user.getIdToken();
    await _persistToken(token);
    return _upsertUser(user, token);
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

  /// Returns the currently authenticated [AppUser] with the plan from the API.
  ///
  /// Returns `null` when no Firebase user is logged in.
  Future<AppUser?> getCurrentUser() async {
    final firebaseUser = _auth.currentUser;
    if (firebaseUser == null) return null;

    final token = await getToken();
    if (token == null) return null;

    try {
      final response = await _dio.get(
        '/auth/me',
        options: Options(
          headers: {'Authorization': 'Bearer $token'},
        ),
      );
      final data = response.data as Map<String, dynamic>;
      final plan = data['plan'] as String? ?? 'free';
      return AppUser(
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? '',
        displayName: firebaseUser.displayName,
        plan: plan,
      );
    } catch (e) {
      developer.log(
        'GET /auth/me failed, returning user without plan: $e',
        name: 'AuthRepository',
      );
      // Return basic user; plan defaults to 'free'.
      return AppUser(
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? '',
        displayName: firebaseUser.displayName,
      );
    }
  }

  /// Stream of raw Firebase [User] auth-state changes.
  ///
  /// Emits `null` when the user signs out.
  Stream<User?> get authStateChanges => _auth.authStateChanges();

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  Future<void> _persistToken(String? token) async {
    if (token != null) {
      await _storage.write(key: _tokenKey, value: token);
    }
  }

  /// Calls POST /auth/register to upsert the user in the backend.
  ///
  /// On network failure the method still returns a valid [AppUser] so that
  /// offline / first-boot scenarios do not block authentication.
  Future<AppUser> _upsertUser(User firebaseUser, String? token) async {
    try {
      final response = await _dio.post(
        '/auth/register',
        options: token != null
            ? Options(headers: {'Authorization': 'Bearer $token'})
            : null,
        data: {
          'uid': firebaseUser.uid,
          'email': firebaseUser.email,
          'display_name': firebaseUser.displayName,
        },
      );
      final data = response.data as Map<String, dynamic>;
      final plan = data['plan'] as String? ?? 'free';
      return AppUser(
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? '',
        displayName: firebaseUser.displayName,
        plan: plan,
      );
    } catch (e) {
      developer.log(
        'POST /auth/register failed, using free plan: $e',
        name: 'AuthRepository',
      );
      return AppUser(
        uid: firebaseUser.uid,
        email: firebaseUser.email ?? '',
        displayName: firebaseUser.displayName,
      );
    }
  }
}

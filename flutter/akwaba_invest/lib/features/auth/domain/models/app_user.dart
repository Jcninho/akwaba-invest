/// Domain model representing an authenticated application user.
///
/// [plan] is either 'free' or 'premium' — sourced from the backend
/// on every auth event via GET /auth/me.
class AppUser {
  final String uid;
  final String email;
  final String? displayName;

  /// 'free' | 'premium'
  final String plan;

  const AppUser({
    required this.uid,
    required this.email,
    this.displayName,
    this.plan = 'free',
  });

  bool get isPremium => plan == 'premium';

  AppUser copyWith({String? plan}) => AppUser(
        uid: uid,
        email: email,
        displayName: displayName,
        plan: plan ?? this.plan,
      );
}

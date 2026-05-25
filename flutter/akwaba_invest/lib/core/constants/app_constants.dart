class AppConstants {
  // API
  static const String apiBaseUrl = 'http://109.123.246.66';
  static const String apiVersion = '/api/v1';
  static const int connectTimeout = 30000;
  static const int receiveTimeout = 30000;

  // Cache
  static const String lastBocSyncKey = 'last_boc_sync';
  static const String userPlanKey = 'user_plan';
  static const String onboardingSeenKey = 'onboarding_seen';

  // Market
  static const int topMoversCount = 5;
  static const int defaultPriceDays = 30;

  // Pagination
  static const int searchMinChars = 2;
}

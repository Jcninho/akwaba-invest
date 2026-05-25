import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/portfolio_repository.dart';

final portfolioRepositoryProvider = Provider<PortfolioRepository>((ref) {
  // TODO: replace Dio() with DioClient.getInstance() via FutureProvider
  return PortfolioRepository(Dio());
});

/// The user's default portfolio with live valuation.
final portfolioProvider =
    AsyncNotifierProvider<PortfolioNotifier, dynamic>(PortfolioNotifier.new);

class PortfolioNotifier extends AsyncNotifier<dynamic> {
  @override
  Future<dynamic> build() async {
    // TODO: call ref.read(portfolioRepositoryProvider).getPortfolio()
    return null;
  }

  Future<void> addLine({
    required String symbol,
    required double quantity,
    required double price,
  }) async {
    // TODO: call repository.addLine() and refresh state
  }

  Future<void> removeLine(int lineId) async {
    // TODO: call repository.removeLine(lineId) and refresh state
  }
}

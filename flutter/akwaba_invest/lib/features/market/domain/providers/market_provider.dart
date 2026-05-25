import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/market_repository.dart';

final marketRepositoryProvider = Provider<MarketRepository>((ref) {
  // TODO: replace Dio() with DioClient.getInstance() via FutureProvider
  return MarketRepository(Dio());
});

/// All active stocks with their latest price.
final stockListProvider =
    AsyncNotifierProvider<StockListNotifier, List<dynamic>>(
        StockListNotifier.new);

class StockListNotifier extends AsyncNotifier<List<dynamic>> {
  @override
  Future<List<dynamic>> build() async {
    // TODO: call ref.read(marketRepositoryProvider).getStocks()
    return [];
  }
}

/// Market summary (indices, advancers/decliners count).
final marketSummaryProvider =
    AsyncNotifierProvider<MarketSummaryNotifier, dynamic>(
        MarketSummaryNotifier.new);

class MarketSummaryNotifier extends AsyncNotifier<dynamic> {
  @override
  Future<dynamic> build() async {
    // TODO: call ref.read(marketRepositoryProvider).getMarketSummary()
    return null;
  }
}

/// Top movers for the current trading session.
final topMoversProvider =
    AsyncNotifierProvider<TopMoversNotifier, dynamic>(TopMoversNotifier.new);

class TopMoversNotifier extends AsyncNotifier<dynamic> {
  @override
  Future<dynamic> build() async {
    // TODO: call ref.read(marketRepositoryProvider).getTopMovers()
    return null;
  }
}

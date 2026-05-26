import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/constants/app_constants.dart';
import '../../data/market_repository.dart';
import '../models/stock_model.dart';

// ---------------------------------------------------------------------------
// Repository provider
// ---------------------------------------------------------------------------

/// Provides a [MarketRepository] backed by a configured [Dio] instance.
///
/// The singleton [DioClient] is async; for simplicity the market repository
/// creates its own [Dio] here. The auth interceptor is not needed for the
/// public market endpoints (they are JWT-protected at the backend but the
/// token is attached by [DioClient]'s interceptor when using the shared
/// instance). TODO(P3-04): switch to DioClient.getInstance() via FutureProvider.
final marketRepositoryProvider = Provider<MarketRepository>((ref) {
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
  return MarketRepository(dio);
});

// ---------------------------------------------------------------------------
// Stock list (main list + pull-to-refresh)
// ---------------------------------------------------------------------------

/// All active stocks with their latest BOC price.
final stockListProvider =
    AsyncNotifierProvider<StockListNotifier, List<StockWithPriceModel>>(
  StockListNotifier.new,
);

class StockListNotifier extends AsyncNotifier<List<StockWithPriceModel>> {
  @override
  Future<List<StockWithPriceModel>> build() =>
      ref.read(marketRepositoryProvider).getStocks();

  /// Triggers a fresh fetch — called by [RefreshIndicator].
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(marketRepositoryProvider).getStocks(),
    );
  }
}

// ---------------------------------------------------------------------------
// Market summary
// ---------------------------------------------------------------------------

/// Market summary (BRVM Composite, advancers/decliners, trading date).
final marketSummaryProvider =
    AsyncNotifierProvider<MarketSummaryNotifier, MarketSummaryModel?>(
  MarketSummaryNotifier.new,
);

class MarketSummaryNotifier extends AsyncNotifier<MarketSummaryModel?> {
  @override
  Future<MarketSummaryModel?> build() async {
    try {
      return await ref.read(marketRepositoryProvider).getMarketSummary();
    } catch (_) {
      // Summary is non-critical; swallow the error so the rest of the
      // screen still renders when the endpoint is unavailable.
      return null;
    }
  }
}

// ---------------------------------------------------------------------------
// Top movers
// ---------------------------------------------------------------------------

/// Top gainers and losers for the latest BOC session.
final topMoversProvider =
    AsyncNotifierProvider<TopMoversNotifier, TopMoversModel?>(
  TopMoversNotifier.new,
);

class TopMoversNotifier extends AsyncNotifier<TopMoversModel?> {
  @override
  Future<TopMoversModel?> build() async {
    try {
      return await ref.read(marketRepositoryProvider).getTopMovers();
    } catch (_) {
      return null;
    }
  }
}

// ---------------------------------------------------------------------------
// Stock search — family keyed by query string
// ---------------------------------------------------------------------------

/// Searches stocks by name / symbol.
///
/// Returns an empty list when [query] is shorter than [AppConstants.searchMinChars].
/// The [FutureProvider.family] caches results per query automatically.
final searchResultsProvider =
    FutureProvider.family<List<StockModel>, String>((ref, query) async {
  if (query.trim().length < AppConstants.searchMinChars) return [];
  return ref.read(marketRepositoryProvider).searchStocks(query.trim());
});

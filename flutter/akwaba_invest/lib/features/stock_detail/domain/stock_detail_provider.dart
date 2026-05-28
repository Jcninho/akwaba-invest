import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/constants/app_constants.dart';
import '../data/stock_detail_repository.dart';
import '../../market/domain/models/stock_model.dart';

// ---------------------------------------------------------------------------
// Repository provider
// ---------------------------------------------------------------------------

/// Provides a [StockDetailRepository] backed by a fresh [Dio] instance.
///
/// Keyed by symbol so each symbol gets its own repository instance.
final stockDetailRepositoryProvider =
    Provider.family<StockDetailRepository, String>((ref, symbol) {
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
  return StockDetailRepository(dio);
});

// ---------------------------------------------------------------------------
// Stock detail
// ---------------------------------------------------------------------------

/// Full detail data for a single stock, keyed by [symbol].
final stockDetailProvider =
    FutureProvider.family<StockDetailModel, String>((ref, symbol) {
  return ref
      .read(stockDetailRepositoryProvider(symbol))
      .getStockDetail(symbol);
});

// ---------------------------------------------------------------------------
// Period selector state
// ---------------------------------------------------------------------------

/// Currently selected chart period in days (7 | 30 | 90 | 365).
///
/// Shared across all stock detail screens — resetting to 30 on each screen
/// open is handled by the screen's [initState]-equivalent (StatefulWidget)
/// or accepted as UX behaviour.
final selectedDaysProvider = StateProvider<int>((ref) => 30);

// ---------------------------------------------------------------------------
// Price history
// ---------------------------------------------------------------------------

/// Daily price history for [symbol], filtered to [selectedDaysProvider] days.
///
/// Automatically rebuilds when [selectedDaysProvider] changes.
final priceHistoryProvider =
    FutureProvider.family<List<DailyPriceModel>, String>((ref, symbol) {
  final days = ref.watch(selectedDaysProvider);
  return ref
      .read(stockDetailRepositoryProvider(symbol))
      .getPriceHistory(symbol, days: days);
});

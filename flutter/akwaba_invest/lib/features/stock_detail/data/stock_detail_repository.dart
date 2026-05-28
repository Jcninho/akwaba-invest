import 'package:dio/dio.dart';

import '../../market/domain/models/stock_model.dart';

/// Handles HTTP calls specific to the stock detail screen.
///
/// Endpoints used:
///   GET /stocks/{symbol}           → full stock detail
///   GET /stocks/{symbol}/prices/   → OHLCV price history (supports ?days=N)
class StockDetailRepository {
  final Dio _dio;

  StockDetailRepository(this._dio);

  /// Returns the full detail data for [symbol].
  Future<StockDetailModel> getStockDetail(String symbol) async {
    final response =
        await _dio.get<Map<String, dynamic>>('/stocks/$symbol');
    return StockDetailModel.fromJson(response.data!);
  }

  /// Returns [days] days of daily price history for [symbol].
  ///
  /// Defaults to 30 days when [days] is omitted.
  Future<List<DailyPriceModel>> getPriceHistory(
    String symbol, {
    int days = 30,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      '/stocks/$symbol/prices/',
      queryParameters: {'days': days},
    );
    return (response.data ?? [])
        .map((e) => DailyPriceModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

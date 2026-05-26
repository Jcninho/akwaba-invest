import 'package:dio/dio.dart';

import '../domain/models/stock_model.dart';

/// Handles all HTTP calls related to stocks and market data.
///
/// Every method maps to one backend route documented in CLAUDE.md.
/// Collection endpoints (those returning lists) always use trailing slash
/// to match FastAPI route definitions:
///   GET /stocks/                   → list of stocks with latest price
///   GET /stocks/summary            → market summary (indices, counts)
///   GET /stocks/top-movers         → top gainers & losers
///   GET /stocks/search?q=…         → search by name / symbol
///   GET /stocks/{symbol}           → full stock detail
///   GET /stocks/{symbol}/prices/   → daily price history
///   GET /stocks/{symbol}/dividends/   → dividend history
///   GET /stocks/{symbol}/financials/  → annual financials
class MarketRepository {
  final Dio _dio;

  MarketRepository(this._dio);

  // ---------------------------------------------------------------------------
  // Market-wide endpoints
  // ---------------------------------------------------------------------------

  /// Returns all active stocks with their latest BOC price.
  ///
  /// Optionally filter by [sector] (e.g. 'FIN', 'TEL').
  Future<List<StockWithPriceModel>> getStocks({String? sector}) async {
    final response = await _dio.get<List<dynamic>>(
      '/stocks/',
      queryParameters: sector != null ? {'sector': sector} : null,
    );
    final items = response.data ?? [];
    return items
        .map((e) => StockWithPriceModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Returns the market summary for the latest BOC session.
  Future<MarketSummaryModel> getMarketSummary() async {
    final response = await _dio.get<Map<String, dynamic>>('/stocks/summary');
    return MarketSummaryModel.fromJson(response.data!);
  }

  /// Returns top gainers and losers for the latest session.
  Future<TopMoversModel> getTopMovers() async {
    final response =
        await _dio.get<Map<String, dynamic>>('/stocks/top-movers');
    return TopMoversModel.fromJson(response.data!);
  }

  /// Searches stocks by name or symbol.
  ///
  /// Returns an empty list when [query] is shorter than 2 characters
  /// (guard is also applied at the provider level).
  Future<List<StockModel>> searchStocks(String query) async {
    final response = await _dio.get<List<dynamic>>(
      '/stocks/search',
      queryParameters: {'q': query},
    );
    final items = response.data ?? [];
    return items
        .map((e) => StockModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // ---------------------------------------------------------------------------
  // Per-stock endpoints
  // ---------------------------------------------------------------------------

  /// Returns the full detail page data for [symbol].
  Future<StockDetailModel> getStockDetail(String symbol) async {
    final response =
        await _dio.get<Map<String, dynamic>>('/stocks/$symbol');
    return StockDetailModel.fromJson(response.data!);
  }

  /// Returns the daily price history for [symbol].
  Future<List<DailyPriceModel>> getStockPrices(String symbol) async {
    final response =
        await _dio.get<List<dynamic>>('/stocks/$symbol/prices/');
    final items = response.data ?? [];
    return items
        .map((e) => DailyPriceModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Returns the dividend history for [symbol].
  Future<List<DividendModel>> getStockDividends(String symbol) async {
    final response =
        await _dio.get<List<dynamic>>('/stocks/$symbol/dividends/');
    final items = response.data ?? [];
    return items
        .map((e) => DividendModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Returns the annual financial data for [symbol].
  Future<List<FinancialModel>> getStockFinancials(String symbol) async {
    final response =
        await _dio.get<List<dynamic>>('/stocks/$symbol/financials/');
    final items = response.data ?? [];
    return items
        .map((e) => FinancialModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

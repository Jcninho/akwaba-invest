import 'package:dio/dio.dart';

class MarketRepository {
  final Dio _dio;

  MarketRepository(this._dio);

  // TODO: GET /stocks → List<StockModel>
  // TODO: GET /stocks?sector=xxx → filtered list
  // TODO: GET /stocks/summary → MarketSummary
  // TODO: GET /stocks/top-movers → TopMovers
  // TODO: GET /stocks/search?q=xxx → List<StockModel>
  // TODO: GET /stocks/{symbol} → StockDetail
  // TODO: GET /stocks/{symbol}/prices → List<DailyPriceModel>
  // TODO: GET /stocks/{symbol}/dividends → List<DividendModel>
  // TODO: GET /stocks/{symbol}/financials → List<FinancialModel>

  /// Placeholder to prevent unused-field warning until methods are implemented.
  Dio get client => _dio;
}

import 'package:dio/dio.dart';

class PortfolioRepository {
  final Dio _dio;

  PortfolioRepository(this._dio);

  Dio get client => _dio;

  // TODO: GET  /portfolio/           → PortfolioRead
  // TODO: POST /portfolio/lines      → PortfolioRead (add/consolidate line)
  // TODO: DELETE /portfolio/lines/{id} → PortfolioRead
  // TODO: POST /portfolio/dividends  → PortfolioRead
  // TODO: GET  /portfolio/portfolios → List<PortfolioSummary>
  // TODO: POST /portfolio/portfolios → PortfolioSummary
}

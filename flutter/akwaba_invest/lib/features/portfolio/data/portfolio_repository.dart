import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../domain/models/portfolio_model.dart';

class PortfolioRepository {
  final Dio _dio;

  PortfolioRepository(this._dio);

  Future<PortfolioModel> getPortfolio() async {
    final response = await _dio.get<Map<String, dynamic>>('/portfolio/');
    return PortfolioModel.fromJson(response.data!);
  }

  Future<PortfolioModel> addLine(
    String symbol,
    double quantity,
    double price,
  ) async {
    // DEBUG — remove after fix
    debugPrint('addLine called: symbol="$symbol" qty=$quantity price=$price');
    final response = await _dio.post<Map<String, dynamic>>(
      '/portfolio/lines',
      data: {
        'symbol': symbol,
        'quantity': quantity.toString(),
        'price': price.toString(),
      },
    );
    return PortfolioModel.fromJson(response.data!);
  }

  Future<PortfolioModel> removeLine(int lineId) async {
    final response = await _dio.delete<Map<String, dynamic>>(
      '/portfolio/lines/$lineId',
    );
    return PortfolioModel.fromJson(response.data!);
  }
}

import 'package:freezed_annotation/freezed_annotation.dart';

part 'portfolio_model.freezed.dart';
part 'portfolio_model.g.dart';

// ---------------------------------------------------------------------------
// JSON converters (mirrors stock_model.dart pattern)
// ---------------------------------------------------------------------------

double? _stringToDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

// Non-nullable variant used for required double fields.
double _stringToDoubleNN(dynamic value) {
  if (value == null) return 0;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? 0;
  return 0;
}

// ---------------------------------------------------------------------------
// PortfolioLineModel — a single position inside a portfolio
// ---------------------------------------------------------------------------

@freezed
class PortfolioLineModel with _$PortfolioLineModel {
  const factory PortfolioLineModel({
    required int id,
    required String symbol,
    @JsonKey(name: 'stock_name') required String stockName,
    required String sector,
    @JsonKey(name: 'avg_price', fromJson: _stringToDoubleNN)
    required double avgPrice,
    @JsonKey(name: 'quantity', fromJson: _stringToDoubleNN)
    required double quantity,
    @JsonKey(name: 'current_price', fromJson: _stringToDouble)
    double? currentPrice,
    @JsonKey(name: 'current_value', fromJson: _stringToDouble)
    double? currentValue,
    @JsonKey(name: 'cost_basis', fromJson: _stringToDoubleNN)
    required double costBasis,
    @JsonKey(name: 'unrealized_gain', fromJson: _stringToDouble)
    double? unrealizedGain,
    @JsonKey(name: 'unrealized_gain_pct', fromJson: _stringToDouble)
    double? unrealizedGainPct,
    @JsonKey(name: 'total_dividends_received', fromJson: _stringToDoubleNN)
    @Default(0)
    double totalDividendsReceived,
    @JsonKey(name: 'total_return', fromJson: _stringToDouble)
    double? totalReturn,
    @JsonKey(name: 'trading_date') String? tradingDate,
  }) = _PortfolioLineModel;

  factory PortfolioLineModel.fromJson(Map<String, dynamic> json) =>
      _$PortfolioLineModelFromJson(json);
}

// ---------------------------------------------------------------------------
// PortfolioModel — full portfolio with aggregated valuation
// ---------------------------------------------------------------------------

@freezed
class PortfolioModel with _$PortfolioModel {
  const factory PortfolioModel({
    required int id,
    required String name,
    @Default([]) List<PortfolioLineModel> lines,
    @JsonKey(name: 'total_value', fromJson: _stringToDouble) double? totalValue,
    @JsonKey(name: 'total_cost', fromJson: _stringToDoubleNN)
    required double totalCost,
    @JsonKey(name: 'total_gain', fromJson: _stringToDouble) double? totalGain,
    @JsonKey(name: 'total_gain_pct', fromJson: _stringToDouble)
    double? totalGainPct,
    @JsonKey(name: 'total_dividends_received', fromJson: _stringToDoubleNN)
    @Default(0)
    double totalDividendsReceived,
    @JsonKey(name: 'total_return', fromJson: _stringToDouble)
    double? totalReturn,
    @JsonKey(name: 'last_updated') String? lastUpdated,
  }) = _PortfolioModel;

  factory PortfolioModel.fromJson(Map<String, dynamic> json) =>
      _$PortfolioModelFromJson(json);
}

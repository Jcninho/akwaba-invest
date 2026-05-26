import 'package:freezed_annotation/freezed_annotation.dart';

part 'stock_model.freezed.dart';
part 'stock_model.g.dart';

// ---------------------------------------------------------------------------
// JSON converter — String | num | null  →  double?
// ---------------------------------------------------------------------------
//
// The PostgreSQL Decimal type is serialised as a JSON string by the backend
// (e.g. "4040.00").  Stocks that have no price row for a given session
// return null for every price field.  This converter handles both cases
// so Freezed models never crash on unexpected types.

/// Converts API decimal strings ("4040.00"), plain numbers, or null to double?.
double? _stringToDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

// ---------------------------------------------------------------------------
// StockModel — base stock reference (no price data)
// ---------------------------------------------------------------------------

@freezed
class StockModel with _$StockModel {
  const factory StockModel({
    required String symbol,
    required String name,
    required String sector,
    required String country,
    @JsonKey(name: 'is_active') @Default(true) bool isActive,
  }) = _StockModel;

  factory StockModel.fromJson(Map<String, dynamic> json) =>
      _$StockModelFromJson(json);
}

// ---------------------------------------------------------------------------
// StockWithPriceModel — stock + latest daily price (used in lists)
// ---------------------------------------------------------------------------

@freezed
class StockWithPriceModel with _$StockWithPriceModel {
  const factory StockWithPriceModel({
    required String symbol,
    required String name,
    required String sector,
    @JsonKey(name: 'close_price', fromJson: _stringToDouble) double? closePrice,
    @JsonKey(name: 'open_price', fromJson: _stringToDouble) double? openPrice,
    @JsonKey(name: 'high_price', fromJson: _stringToDouble) double? highPrice,
    @JsonKey(name: 'low_price', fromJson: _stringToDouble) double? lowPrice,
    @JsonKey(name: 'variation_pct', fromJson: _stringToDouble)
    double? variationPct,
    int? volume,
    @JsonKey(name: 'trading_date') String? tradingDate,
  }) = _StockWithPriceModel;

  factory StockWithPriceModel.fromJson(Map<String, dynamic> json) =>
      _$StockWithPriceModelFromJson(json);
}

// ---------------------------------------------------------------------------
// MarketSummaryModel — indices + advancers/decliners counts
// ---------------------------------------------------------------------------

@freezed
class MarketSummaryModel with _$MarketSummaryModel {
  const factory MarketSummaryModel({
    @JsonKey(name: 'total_stocks') required int totalStocks,
    @JsonKey(name: 'stocks_up') required int stocksUp,
    @JsonKey(name: 'stocks_down') required int stocksDown,
    @JsonKey(name: 'stocks_unchanged') required int stocksUnchanged,
    @JsonKey(name: 'trading_date') required String tradingDate,
    @JsonKey(name: 'brvm_composite', fromJson: _stringToDouble)
    double? brvmComposite,
    @JsonKey(name: 'brvm_composite_variation', fromJson: _stringToDouble)
    double? brvmCompositeVariation,
  }) = _MarketSummaryModel;

  factory MarketSummaryModel.fromJson(Map<String, dynamic> json) =>
      _$MarketSummaryModelFromJson(json);
}

// ---------------------------------------------------------------------------
// TopMoversModel — top gainers and losers for the session
// ---------------------------------------------------------------------------

@freezed
class TopMoversModel with _$TopMoversModel {
  const factory TopMoversModel({
    @JsonKey(name: 'gainers')  // ← était 'top_gainers'
    required List<StockWithPriceModel> topGainers,
    @JsonKey(name: 'losers')   // ← était 'top_losers'
    required List<StockWithPriceModel> topLosers,
    @JsonKey(name: 'trading_date') String? tradingDate,
  }) = _TopMoversModel;

  factory TopMoversModel.fromJson(Map<String, dynamic> json) =>
      _$TopMoversModelFromJson(json);
}

// ---------------------------------------------------------------------------
// DailyPriceModel — OHLCV row for a single trading session
// ---------------------------------------------------------------------------

@freezed
class DailyPriceModel with _$DailyPriceModel {
  const factory DailyPriceModel({
    @JsonKey(name: 'trading_date') required String tradingDate,
    @JsonKey(name: 'open_price', fromJson: _stringToDouble) double? openPrice,
    @JsonKey(name: 'close_price', fromJson: _stringToDouble) double? closePrice,
    @JsonKey(name: 'high_price', fromJson: _stringToDouble) double? highPrice,
    @JsonKey(name: 'low_price', fromJson: _stringToDouble) double? lowPrice,
    int? volume,
    @JsonKey(name: 'variation_pct', fromJson: _stringToDouble)
    double? variationPct,
  }) = _DailyPriceModel;

  factory DailyPriceModel.fromJson(Map<String, dynamic> json) =>
      _$DailyPriceModelFromJson(json);
}

// ---------------------------------------------------------------------------
// DividendModel — annual dividend event
// ---------------------------------------------------------------------------

@freezed
class DividendModel with _$DividendModel {
  const factory DividendModel({
    @JsonKey(name: 'fiscal_year') required int fiscalYear,
    @JsonKey(name: 'gross_amount', fromJson: _stringToDouble)
    double? grossAmount,
    @JsonKey(name: 'net_amount', fromJson: _stringToDouble) double? netAmount,
    @JsonKey(name: 'detachment_date') String? detachmentDate,
    @JsonKey(name: 'payment_date') String? paymentDate,
    @JsonKey(name: 'is_confirmed') @Default(false) bool isConfirmed,
  }) = _DividendModel;

  factory DividendModel.fromJson(Map<String, dynamic> json) =>
      _$DividendModelFromJson(json);
}

// ---------------------------------------------------------------------------
// FinancialModel — annual financials (CA, résultat, PER…)
// ---------------------------------------------------------------------------

@freezed
class FinancialModel with _$FinancialModel {
  const factory FinancialModel({
    @JsonKey(name: 'fiscal_year') required int fiscalYear,
    @JsonKey(fromJson: _stringToDouble) double? revenue,
    @JsonKey(name: 'net_income', fromJson: _stringToDouble) double? netIncome,
    @JsonKey(fromJson: _stringToDouble) double? eps,
    @JsonKey(fromJson: _stringToDouble) double? per,
    @JsonKey(name: 'dividend_yield', fromJson: _stringToDouble)
    double? dividendYield,
  }) = _FinancialModel;

  factory FinancialModel.fromJson(Map<String, dynamic> json) =>
      _$FinancialModelFromJson(json);
}

// ---------------------------------------------------------------------------
// StockDetailModel — full stock page data
// ---------------------------------------------------------------------------

@freezed
class StockDetailModel with _$StockDetailModel {
  const factory StockDetailModel({
    required String symbol,
    required String name,
    required String sector,
    required String country,
    @JsonKey(name: 'latest_price') StockWithPriceModel? latestPrice,
    @JsonKey(name: 'latest_dividend') DividendModel? latestDividend,
    @Default([]) List<FinancialModel> financials,
  }) = _StockDetailModel;

  factory StockDetailModel.fromJson(Map<String, dynamic> json) =>
      _$StockDetailModelFromJson(json);
}

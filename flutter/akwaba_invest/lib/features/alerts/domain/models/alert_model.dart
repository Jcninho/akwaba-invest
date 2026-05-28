import 'package:freezed_annotation/freezed_annotation.dart';

part 'alert_model.freezed.dart';
part 'alert_model.g.dart';

double? _stringToDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

@freezed
class AlertModel with _$AlertModel {
  const factory AlertModel({
    required int id,
    required String symbol,
    @JsonKey(name: 'stock_name') String? stockName,
    @JsonKey(name: 'alert_type') required String alertType,
    @JsonKey(fromJson: _stringToDouble) double? threshold,
    @JsonKey(name: 'is_active') required bool isActive,
    @JsonKey(name: 'last_triggered_at') String? lastTriggeredAt,
  }) = _AlertModel;

  factory AlertModel.fromJson(Map<String, dynamic> json) =>
      _$AlertModelFromJson(json);
}

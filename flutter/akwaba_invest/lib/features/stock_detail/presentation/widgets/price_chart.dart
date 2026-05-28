import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../../market/domain/models/stock_model.dart';

/// LineChart widget for the stock detail price history section.
///
/// Shows [prices] as a smooth line over time. If fewer than 2 data points
/// have a non-null [DailyPriceModel.closePrice], displays an empty state.
class PriceChart extends StatelessWidget {
  const PriceChart({
    super.key,
    required this.prices,
    this.lineColor,
  });

  final List<DailyPriceModel> prices;

  /// Overrides the default green colour (used to show red for losing sessions).
  final Color? lineColor;

  String _formatAxisPrice(double value) {
    final int intVal = value.toInt();
    if (intVal <= 0) return '0';
    final digits = intVal.abs().toString().split('').reversed.toList();
    final withSpaces = <String>[];
    for (var i = 0; i < digits.length; i++) {
      if (i != 0 && i % 3 == 0) withSpaces.add(' ');
      withSpaces.add(digits[i]);
    }
    return withSpaces.reversed.join();
  }

  @override
  Widget build(BuildContext context) {
    final validPrices =
        prices.where((p) => p.closePrice != null).toList();

    if (validPrices.length < 2) {
      return const Center(
        child: Text(
          'Données insuffisantes',
          style: TextStyle(color: AppColors.grey, fontSize: 13),
        ),
      );
    }

    final spots = <FlSpot>[];
    final dates = <DateTime>[];
    for (var i = 0; i < validPrices.length; i++) {
      final p = validPrices[i];
      final closePrice = p.closePrice;
      if (closePrice == null) continue;
      spots.add(FlSpot(i.toDouble(), closePrice));
      final parsed = DateTime.tryParse(p.tradingDate);
      dates.add(parsed ?? DateTime.now());
    }

    final minY = spots.map((s) => s.y).reduce((a, b) => a < b ? a : b);
    final maxY = spots.map((s) => s.y).reduce((a, b) => a > b ? a : b);
    final yRange = maxY - minY;
    final yPadding = yRange > 0 ? yRange * 0.15 : 500.0;
    final hInterval = yRange > 0 ? yRange / 4 : 1000.0;

    final color = lineColor ?? AppColors.green;
    final step = ((spots.length / 4).ceil()).clamp(1, spots.length);

    return LineChart(
      LineChartData(
        minX: 0,
        maxX: (spots.length - 1).toDouble(),
        minY: minY - yPadding,
        maxY: maxY + yPadding,
        clipData: const FlClipData.all(),
        lineBarsData: [
          LineChartBarData(
            spots: spots,
            isCurved: true,
            color: color,
            barWidth: 2,
            dotData: const FlDotData(show: false),
            belowBarData: BarAreaData(
              show: true,
              color: color.withValues(alpha: 0.08),
            ),
          ),
        ],
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 60,
              getTitlesWidget: (value, meta) => Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Text(
                  _formatAxisPrice(value),
                  style: const TextStyle(
                    color: AppColors.grey,
                    fontSize: 9,
                  ),
                ),
              ),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 24,
              getTitlesWidget: (value, meta) {
                final idx = value.toInt();
                if (idx % step != 0 || idx >= dates.length) {
                  return const SizedBox.shrink();
                }
                final d = dates[idx];
                return Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '${d.day}/${d.month}',
                    style: const TextStyle(
                      color: AppColors.grey,
                      fontSize: 9,
                    ),
                  ),
                );
              },
            ),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          horizontalInterval: hInterval,
          getDrawingHorizontalLine: (_) => const FlLine(
            color: AppColors.greyLine,
            strokeWidth: 1,
          ),
        ),
        borderData: FlBorderData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipColor: (_) => AppColors.darkBlue,
            getTooltipItems: (touchedSpots) => touchedSpots.map((spot) {
              final idx = spot.x.toInt();
              final dateStr =
                  idx < dates.length ? formatShortDate(dates[idx]) : '';
              return LineTooltipItem(
                '$dateStr\n${formatFcfa(spot.y)}',
                const TextStyle(
                  color: AppColors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}

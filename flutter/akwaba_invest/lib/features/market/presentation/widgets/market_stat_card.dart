import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

/// Small card displaying a single market statistic.
///
/// Used in the summary row for: BRVM Composite, Nb Hausse, Nb Baisse.
///
/// Example:
/// ```dart
/// MarketStatCard(
///   label: 'BRVM Composite',
///   value: '215.34',
///   valueColor: AppColors.priceUp,
/// )
/// ```
class MarketStatCard extends StatelessWidget {
  const MarketStatCard({
    super.key,
    required this.label,
    required this.value,
    this.valueColor,
  });

  final String label;
  final String value;

  /// Optional colour for [value] text (e.g. green/red for market direction).
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(10),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A000000),
            blurRadius: 6,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: AppColors.grey,
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? AppColors.darkBlue,
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

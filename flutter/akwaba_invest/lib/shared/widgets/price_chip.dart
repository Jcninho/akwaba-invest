import 'package:flutter/material.dart';
import '../../core/utils/formatters.dart';

/// Displays a variation percentage with a colored background chip.
///
/// Example:
///   PriceChip(variation: -0.35) → red chip "-0.35%"
///   PriceChip(variation: 0.17)  → green chip "+0.17%"
class PriceChip extends StatelessWidget {
  const PriceChip({
    super.key,
    required this.variation,
    this.showSign = true,
  });

  final double variation;

  /// When false, the +/− sign is stripped from the displayed text.
  final bool showSign;

  @override
  Widget build(BuildContext context) {
    final color = variationColor(variation);
    final bgColor = variationBgColor(variation);
    final raw = formatVariation(variation);
    final text = showSign ? raw : raw.replaceFirst('+', '').replaceFirst('-', '');

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

/// Format a number as a French-style FCFA amount.
/// Example: 28900 → "28 900 FCFA"
String formatFcfa(num amount) {
  final digits = amount.toInt().abs().toString().split('').reversed.toList();
  final withSpaces = <String>[];
  for (var i = 0; i < digits.length; i++) {
    if (i != 0 && i % 3 == 0) withSpaces.add(' ');
    withSpaces.add(digits[i]);
  }
  final formatted = withSpaces.reversed.join();
  return '${amount < 0 ? '-' : ''}$formatted FCFA';
}

/// Format a variation percentage with sign.
/// Example: -0.35 → "-0.35%", 0.17 → "+0.17%", 0.0 → "0.00%"
String formatVariation(double pct) {
  if (pct == 0.0) return '0.00%';
  final sign = pct > 0 ? '+' : '';
  return '$sign${pct.toStringAsFixed(2)}%';
}

/// Format a DateTime as a French long date.
/// Example: DateTime(2026, 5, 18) → "18 mai 2026"
String formatDate(DateTime date) {
  const months = [
    'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
    'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre',
  ];
  return '${date.day} ${months[date.month - 1]} ${date.year}';
}

/// Format a DateTime as DD/MM/YYYY.
/// Example: DateTime(2026, 5, 18) → "18/05/2026"
String formatShortDate(DateTime date) {
  final d = date.day.toString().padLeft(2, '0');
  final m = date.month.toString().padLeft(2, '0');
  return '$d/$m/${date.year}';
}

/// Return the foreground color for a variation percentage.
Color variationColor(double pct) {
  if (pct > 0) return AppColors.priceUp;
  if (pct < 0) return AppColors.priceDown;
  return AppColors.priceUnchanged;
}

/// Return the background color for a variation percentage chip.
Color variationBgColor(double pct) {
  if (pct > 0) return AppColors.priceUpBg;
  if (pct < 0) return AppColors.priceDownBg;
  return AppColors.white;
}

import 'package:flutter/material.dart';

import '../../../../../core/theme/app_colors.dart';

/// Row of period-selector buttons: 7j | 30j | 90j | 1an.
///
/// The selected button has a green background with white text.
/// Unselected buttons have a white background with grey text.
class PeriodSelector extends StatelessWidget {
  const PeriodSelector({
    super.key,
    required this.selectedDays,
    required this.onChanged,
  });

  final int selectedDays;
  final void Function(int days) onChanged;

  static const List<({int days, String label})> _periods = [
    (days: 7, label: '7j'),
    (days: 30, label: '30j'),
    (days: 90, label: '90j'),
    (days: 365, label: '1an'),
  ];

  @override
  Widget build(BuildContext context) {
    return Row(
      children: _periods.map((p) {
        final isSelected = p.days == selectedDays;
        return Padding(
          padding: const EdgeInsets.only(right: 8),
          child: GestureDetector(
            onTap: () => onChanged(p.days),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
              decoration: BoxDecoration(
                color: isSelected ? AppColors.green : AppColors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected ? AppColors.green : AppColors.greyLine,
                ),
              ),
              child: Text(
                p.label,
                style: TextStyle(
                  color: isSelected ? AppColors.white : AppColors.grey,
                  fontSize: 13,
                  fontWeight:
                      isSelected ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

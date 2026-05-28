import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../domain/models/alert_model.dart';
import '../../domain/providers/alerts_provider.dart';

class AlertTile extends ConsumerWidget {
  const AlertTile({super.key, required this.alert});

  final AlertModel alert;

  String get _typeLabel {
    switch (alert.alertType) {
      case 'price_above':
        return 'Hausse au-dessus de';
      case 'price_below':
        return 'Baisse sous';
      case 'dividend':
        return 'Nouveau dividende';
      default:
        return alert.alertType;
    }
  }

  IconData get _typeIcon {
    switch (alert.alertType) {
      case 'price_above':
        return Icons.arrow_upward;
      case 'price_below':
        return Icons.arrow_downward;
      default:
        return Icons.payments;
    }
  }

  Color get _iconColor {
    switch (alert.alertType) {
      case 'price_above':
        return AppColors.green;
      case 'price_below':
        return AppColors.priceDown;
      default:
        return const Color(0xFF1565C0);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lastTriggered = alert.lastTriggeredAt != null
        ? DateTime.tryParse(alert.lastTriggeredAt!)
        : null;

    return Dismissible(
      key: ValueKey(alert.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        color: AppColors.priceDown,
        child: const Icon(Icons.delete, color: AppColors.white),
      ),
      onDismissed: (_) =>
          ref.read(alertsProvider.notifier).deleteAlert(alert.id),
      child: Card(
        color: AppColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: AppColors.greyLine),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: ListTile(
          leading: CircleAvatar(
            backgroundColor: _iconColor.withValues(alpha: 0.12),
            child: Icon(_typeIcon, color: _iconColor, size: 20),
          ),
          title: Text(
            '${alert.symbol} — $_typeLabel',
            style: const TextStyle(
              color: AppColors.darkBlue,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                alert.alertType == 'dividend'
                    ? 'Alerte dividende'
                    : formatFcfa(alert.threshold),
                style: const TextStyle(
                  color: AppColors.grey,
                  fontSize: 13,
                ),
              ),
              if (lastTriggered != null)
                Text(
                  'Déclenchée le ${formatDate(lastTriggered)}',
                  style: const TextStyle(
                    color: AppColors.orange,
                    fontSize: 11,
                  ),
                ),
            ],
          ),
          isThreeLine: lastTriggered != null,
          trailing: Switch(
            value: alert.isActive,
            activeThumbColor: AppColors.green,
            onChanged: (val) => ref
                .read(alertsProvider.notifier)
                .toggleAlert(alert.id, isActive: val),
          ),
        ),
      ),
    );
  }
}

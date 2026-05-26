import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../../../shared/widgets/price_chip.dart';
import '../../domain/models/stock_model.dart';

/// A [ListTile] representing one stock in the main market list.
///
/// Leading : colored dot keyed on sector code.
/// Title   : stock name (bold).
/// Subtitle: stock symbol (grey).
/// Trailing: close price + [PriceChip] showing the daily variation.
/// Tap     : navigates to /stock/:symbol via GoRouter.
class StockListTile extends StatelessWidget {
  const StockListTile({super.key, required this.stock});

  final StockWithPriceModel stock;

  // Sector → colour mapping (BRVM sector codes)
  static const Map<String, Color> _sectorColors = {
    'TEL': Color(0xFF3B82F6), // blue
    'FIN': Color(0xFF10B981), // green
    'CB':  Color(0xFFF97316), // orange
    'CD':  Color(0xFF8B5CF6), // purple
    'IND': Color(0xFF92400E), // brown
    'ENE': Color(0xFFF59E0B), // yellow
    'SPU': Color(0xFF14B8A6), // teal
  };

  @override
  Widget build(BuildContext context) {
    final sectorColor = _sectorColors[stock.sector] ?? AppColors.grey;

    return Column(
      children: [
        ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          leading: Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: sectorColor,
              shape: BoxShape.circle,
            ),
          ),
          title: Text(
            stock.name,
            style: const TextStyle(
              fontWeight: FontWeight.w600,
              fontSize: 14,
              color: AppColors.darkBlue,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          subtitle: Text(
            stock.symbol,
            style: const TextStyle(color: AppColors.grey, fontSize: 12),
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                formatFcfa(stock.closePrice),
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                  color: AppColors.darkBlue,
                ),
              ),
              const SizedBox(height: 4),
              PriceChip(variation: stock.variationPct),
            ],
          ),
          onTap: () => context.go('/stock/${stock.symbol}'),
        ),
        const Divider(height: 1, indent: 16, endIndent: 16),
      ],
    );
  }
}

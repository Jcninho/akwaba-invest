import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../../../shared/widgets/price_chip.dart';
import '../../domain/models/stock_model.dart';

/// Compact card displayed in the horizontal top-movers list.
///
/// Fixed size: 140 × 100 px.
/// Tap navigates to /stock/:symbol.
class TopMoverCard extends StatelessWidget {
  const TopMoverCard({super.key, required this.stock});

  final StockWithPriceModel stock;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => context.go('/stock/${stock.symbol}'),
      child: Container(
        width: 140,
        height: 100,
        margin: const EdgeInsets.only(right: 12),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppColors.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: const [
            BoxShadow(
              color: Color(0x12000000),
              blurRadius: 8,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Symbol
            Text(
              stock.symbol,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: AppColors.darkBlue,
                fontSize: 13,
              ),
            ),
            // Name — max 2 lines
            Text(
              stock.name,
              style: const TextStyle(color: AppColors.grey, fontSize: 10),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            // Price + chip
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  formatFcfa(stock.closePrice),
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 11,
                    color: AppColors.darkBlue,
                  ),
                ),
                const SizedBox(height: 2),
                PriceChip(variation: stock.variationPct),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

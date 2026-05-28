import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../../../shared/widgets/price_chip.dart';
import '../../domain/models/portfolio_model.dart';
import '../../domain/portfolio_provider.dart';

/// Card displaying a single portfolio position.
///
/// Swipe left to reveal the delete action. A confirmation dialog is shown
/// before the position is removed via [portfolioProvider].
class PortfolioLineTile extends ConsumerWidget {
  const PortfolioLineTile({super.key, required this.line});

  final PortfolioLineModel line;

  Color _gainColor(double? gain) {
    if (gain == null || gain == 0) return AppColors.grey;
    return gain > 0 ? AppColors.priceUp : AppColors.priceDown;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final gainColor = _gainColor(line.unrealizedGain);

    return Dismissible(
      key: ValueKey(line.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        color: AppColors.priceDown,
        child: const Icon(Icons.delete_outline_rounded, color: AppColors.white),
      ),
      confirmDismiss: (_) async {
        return await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Supprimer la position'),
            content: Text(
              'Retirer ${line.symbol} — ${line.stockName} de votre portefeuille ?',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Annuler'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: Text(
                  'Supprimer',
                  style: TextStyle(color: AppColors.priceDown),
                ),
              ),
            ],
          ),
        );
      },
      onDismissed: (_) {
        ref.read(portfolioProvider.notifier).removeLine(line.id);
      },
      child: Card(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        color: AppColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: AppColors.greyLine),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Row 1: symbol + current value
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    line.symbol,
                    style: const TextStyle(
                      color: AppColors.darkBlue,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                  Text(
                    formatFcfa(line.currentValue),
                    style: const TextStyle(
                      color: AppColors.darkBlue,
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              // Row 2: stock name + absolute gain/loss
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      line.stockName,
                      style: const TextStyle(
                        color: AppColors.grey,
                        fontSize: 12,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    formatFcfa(line.unrealizedGain),
                    style: TextStyle(
                      color: gainColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              // Row 3: qty × PRU + variation percentage chip
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${line.quantity.toStringAsFixed(0)} × ${formatFcfa(line.avgPrice)}',
                    style: const TextStyle(
                      color: AppColors.grey,
                      fontSize: 12,
                    ),
                  ),
                  PriceChip(variation: line.unrealizedGainPct),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

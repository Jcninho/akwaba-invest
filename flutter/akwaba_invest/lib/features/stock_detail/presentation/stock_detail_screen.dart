import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/formatters.dart';
import '../../../shared/widgets/error_widget.dart';
import '../../../shared/widgets/loading_shimmer.dart';
import '../../../shared/widgets/price_chip.dart';
import '../../market/domain/models/stock_model.dart';
import '../domain/stock_detail_provider.dart';
import '../../alerts/presentation/widgets/create_alert_sheet.dart';
import '../../portfolio/presentation/widgets/add_position_sheet.dart';
import 'widgets/info_row.dart';
import 'widgets/period_selector.dart';
import 'widgets/price_chart.dart';

class StockDetailScreen extends ConsumerWidget {
  const StockDetailScreen({super.key, required this.symbol});

  final String symbol;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(stockDetailProvider(symbol));
    final historyAsync = ref.watch(priceHistoryProvider(symbol));
    final selectedDays = ref.watch(selectedDaysProvider);

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        title: Text(symbol),
        backgroundColor: AppColors.darkBlue,
        foregroundColor: AppColors.white,
        elevation: 0,
      ),
      body: detailAsync.when(
        loading: _buildLoading,
        error: (e, _) => AkwabaErrorWidget(
          message: 'Impossible de charger la fiche action.',
          onRetry: () => ref.refresh(stockDetailProvider(symbol)),
        ),
        data: (detail) => _buildContent(
          context,
          ref,
          detail,
          historyAsync,
          selectedDays,
        ),
      ),
    );
  }

  Widget _buildLoading() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const LoadingShimmer(width: double.infinity, height: 140),
          const SizedBox(height: 12),
          const LoadingShimmer(width: double.infinity, height: 260),
          const SizedBox(height: 12),
          const LoadingShimmer(width: double.infinity, height: 160),
        ],
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    StockDetailModel detail,
    AsyncValue<List<DailyPriceModel>> historyAsync,
    int selectedDays,
  ) {
    final variation = detail.latestPrice?.variationPct;
    final lineColor =
        (variation != null && variation < 0) ? AppColors.priceDown : AppColors.green;

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // ── Section 1: Hero price card ────────────────────────────────────
          _HeroPriceCard(detail: detail),
          const SizedBox(height: 12),

          // ── Section 2: Price chart ────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  PeriodSelector(
                    selectedDays: selectedDays,
                    onChanged: (days) =>
                        ref.read(selectedDaysProvider.notifier).state = days,
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    height: 200,
                    child: historyAsync.when(
                      loading: () => const LoadingShimmer(
                        width: double.infinity,
                        height: 200,
                      ),
                      error: (_, __) => const Center(
                        child: Text(
                          'Données insuffisantes',
                          style: TextStyle(color: AppColors.grey),
                        ),
                      ),
                      data: (prices) => PriceChart(
                        prices: prices,
                        lineColor: lineColor,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // ── Section 3: Key info card ──────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: _SectionCard(
              title: 'Informations clés',
              child: Column(
                children: [
                  InfoRow(label: 'Secteur', value: detail.sector),
                  const InfoRow(label: 'Variation annuelle', value: '—'),
                  const InfoRow(label: 'PER', value: '—'),
                  const InfoRow(label: 'Volume moyen', value: '—'),
                ],
              ),
            ),
          ),

          // ── Section 4: Dividend card ──────────────────────────────────────
          if (detail.latestDividend case final div?) ...[
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: _DividendCard(
                dividend: div,
                currentPrice: detail.latestPrice?.closePrice,
              ),
            ),
          ],

          const SizedBox(height: 24),

          // ── Section 5: Action buttons ─────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () => showModalBottomSheet<void>(
                      context: context,
                      isScrollControlled: true,
                      backgroundColor: AppColors.white,
                      shape: const RoundedRectangleBorder(
                        borderRadius:
                            BorderRadius.vertical(top: Radius.circular(20)),
                      ),
                      builder: (_) =>
                          AddPositionSheet(prefilledSymbol: symbol),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.green,
                      foregroundColor: AppColors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text(
                      'Ajouter au portefeuille',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () => showModalBottomSheet<void>(
                      context: context,
                      isScrollControlled: true,
                      backgroundColor: AppColors.white,
                      shape: const RoundedRectangleBorder(
                        borderRadius:
                            BorderRadius.vertical(top: Radius.circular(20)),
                      ),
                      builder: (_) =>
                          CreateAlertSheet(prefilledSymbol: symbol),
                    ),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.darkBlue,
                      side: const BorderSide(color: AppColors.darkBlue),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text(
                      'Créer une alerte',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

// ── Hero price card ───────────────────────────────────────────────────────────

class _HeroPriceCard extends StatelessWidget {
  const _HeroPriceCard({required this.detail});

  final StockDetailModel detail;

  @override
  Widget build(BuildContext context) {
    final price = detail.latestPrice;
    final tradingDate =
        price != null ? DateTime.tryParse(price.tradingDate) : null;

    return Container(
      color: AppColors.darkBlue,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            detail.name,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text(
                formatFcfa(price?.closePrice),
                style: const TextStyle(
                  color: AppColors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 12),
              PriceChip(variation: price?.variationPct),
            ],
          ),
          if (tradingDate != null) ...[
            const SizedBox(height: 4),
            Text(
              'Session du ${formatDate(tradingDate)}',
              style: const TextStyle(
                color: Color(0xFFCBD5E0),
                fontSize: 12,
              ),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              _MiniStat(
                label: 'Ouverture',
                value: formatFcfa(price?.openPrice),
              ),
              const _StatDivider(),
              _MiniStat(
                label: 'Volume',
                value: price?.volume != null ? '${price?.volume}' : '—',
              ),
              const _StatDivider(),
              _MiniStat(
                label: 'Haut / Bas',
                value:
                    '${formatFcfa(price?.highPrice)} / ${formatFcfa(price?.lowPrice)}',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Color(0xFF90A4B4),
              fontSize: 10,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

class _StatDivider extends StatelessWidget {
  const _StatDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 28,
      margin: const EdgeInsets.symmetric(horizontal: 12),
      color: const Color(0xFF2D4A5F),
    );
  }
}

// ── Reusable section card ─────────────────────────────────────────────────────

class _SectionCard extends StatelessWidget {
  const _SectionCard({this.title, required this.child});

  final String? title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: AppColors.card,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.greyLine),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title case final t?) ...[
              Text(
                t,
                style: const TextStyle(
                  color: AppColors.darkBlue,
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              const Divider(color: AppColors.greyLine),
            ],
            child,
          ],
        ),
      ),
    );
  }
}

// ── Dividend card ─────────────────────────────────────────────────────────────

class _DividendCard extends StatelessWidget {
  const _DividendCard({
    required this.dividend,
    this.currentPrice,
  });

  final DividendModel dividend;
  final double? currentPrice;

  @override
  Widget build(BuildContext context) {
    final paymentDate = dividend.paymentDate != null
        ? DateTime.tryParse(dividend.paymentDate!)
        : null;

    final netAmount = dividend.netAmount;
    final price = currentPrice;
    final dividendYield =
        (netAmount != null && price != null && price > 0)
            ? (netAmount / price * 100)
            : null;

    return _SectionCard(
      title: 'Dernier dividende',
      child: Column(
        children: [
          InfoRow(
            label: 'Montant net',
            value: formatFcfa(dividend.netAmount),
            valueColor: AppColors.green,
          ),
          InfoRow(
            label: 'Année fiscale',
            value: '${dividend.fiscalYear}',
          ),
          InfoRow(
            label: 'Date paiement',
            value: paymentDate != null ? formatDate(paymentDate) : '—',
          ),
          InfoRow(
            label: 'Rendement',
            value: dividendYield != null
                ? '${dividendYield.toStringAsFixed(2)}%'
                : '—',
            valueColor: dividendYield != null ? AppColors.green : null,
          ),
        ],
      ),
    );
  }
}

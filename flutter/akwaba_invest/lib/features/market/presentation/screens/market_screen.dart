import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../../../shared/widgets/empty_state_widget.dart';
import '../../../../shared/widgets/error_widget.dart';
import '../../../../shared/widgets/loading_shimmer.dart';
import '../../domain/models/stock_model.dart';
import '../../domain/providers/market_provider.dart';
import '../widgets/market_stat_card.dart';
import '../widgets/stock_list_tile.dart';
import '../widgets/stock_search_delegate.dart';
import '../widgets/top_mover_card.dart';

class MarketScreen extends ConsumerWidget {
  const MarketScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summaryState = ref.watch(marketSummaryProvider);
    final topMoversState = ref.watch(topMoversProvider);
    final stockListState = ref.watch(stockListProvider);

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        title: const Text('Marché BRVM'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Rechercher',
            onPressed: () => showSearch(
              context: context,
              delegate: StockSearchDelegate(),
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppColors.green,
        onRefresh: () => ref.read(stockListProvider.notifier).refresh(),
        child: CustomScrollView(
          slivers: [
            // ── Market summary stats ────────────────────────────────────────
            SliverToBoxAdapter(
              child: summaryState.when(
                loading: () => const _SummaryShimmer(),
                error: (_, __) => const SizedBox.shrink(),
                data: (summary) => summary == null
                    ? const SizedBox.shrink()
                    : _SummarySection(summary: summary),
              ),
            ),

            // ── Top movers ──────────────────────────────────────────────────
            SliverToBoxAdapter(
              child: topMoversState.when(
                loading: () => const _TopMoversShimmer(),
                error: (_, __) => const SizedBox.shrink(),
                data: (movers) => movers == null
                    ? const SizedBox.shrink()
                    : _TopMoversSection(movers: movers),
              ),
            ),

            // ── Section header ──────────────────────────────────────────────
            const SliverToBoxAdapter(
              child: Padding(
                padding: EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: Text(
                  'Toutes les actions',
                  style: TextStyle(
                    color: AppColors.darkBlue,
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
              ),
            ),

            // ── Stock list ──────────────────────────────────────────────────
            stockListState.when(
              loading: () => SliverList(
                delegate: SliverChildBuilderDelegate(
                  (_, __) => const _StockTileShimmer(),
                  childCount: 12,
                ),
              ),
              error: (e, _) => SliverFillRemaining(
                child: AkwabaErrorWidget(
                  message: 'Impossible de charger les actions.\nVérifiez votre connexion.',
                  onRetry: () => ref.read(stockListProvider.notifier).refresh(),
                ),
              ),
              data: (stocks) {
                if (stocks.isEmpty) {
                  return const SliverFillRemaining(
                    child: EmptyStateWidget(
                      message: 'Aucune action disponible pour le moment.',
                      icon: Icons.show_chart,
                    ),
                  );
                }
                return SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (_, i) => StockListTile(stock: stocks[i]),
                    childCount: stocks.length,
                  ),
                );
              },
            ),

            // Bottom padding for last item visibility above nav bar
            const SliverToBoxAdapter(child: SizedBox(height: 24)),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Summary section
// ---------------------------------------------------------------------------

class _SummarySection extends StatelessWidget {
  const _SummarySection({required this.summary});

  final MarketSummaryModel summary;

  @override
  Widget build(BuildContext context) {
    final compositeValue = summary.brvmComposite != null
        ? summary.brvmComposite!.toStringAsFixed(2)
        : '—';
    final compositeVariation = summary.brvmCompositeVariation;
    final compositeColor = compositeVariation == null
        ? null
        : variationColor(compositeVariation);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Session du ${summary.tradingDate}',
            style: const TextStyle(color: AppColors.grey, fontSize: 12),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: MarketStatCard(
                  label: 'BRVM Composite',
                  value: compositeValue,
                  valueColor: compositeColor,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: MarketStatCard(
                  label: 'Nb Hausse',
                  value: '${summary.stocksUp}',
                  valueColor: AppColors.priceUp,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: MarketStatCard(
                  label: 'Nb Baisse',
                  value: '${summary.stocksDown}',
                  valueColor: AppColors.priceDown,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Top movers section
// ---------------------------------------------------------------------------

class _TopMoversSection extends StatelessWidget {
  const _TopMoversSection({required this.movers});

  final TopMoversModel movers;

  @override
  Widget build(BuildContext context) {
    final gainers = movers.topGainers;
    if (gainers.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: Text(
            'Meilleures hausses',
            style: TextStyle(
              color: AppColors.darkBlue,
              fontWeight: FontWeight.bold,
              fontSize: 15,
            ),
          ),
        ),
        SizedBox(
          height: 108,
          child: ListView.builder(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.only(left: 16),
            itemCount: gainers.length,
            itemBuilder: (_, i) => TopMoverCard(stock: gainers[i]),
          ),
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Shimmer placeholders
// ---------------------------------------------------------------------------

class _SummaryShimmer extends StatelessWidget {
  const _SummaryShimmer();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          Expanded(
            flex: 2,
            child: LoadingShimmer(width: double.infinity, height: 54),
          ),
          const SizedBox(width: 8),
          Expanded(child: LoadingShimmer(width: double.infinity, height: 54)),
          const SizedBox(width: 8),
          Expanded(child: LoadingShimmer(width: double.infinity, height: 54)),
        ],
      ),
    );
  }
}

class _TopMoversShimmer extends StatelessWidget {
  const _TopMoversShimmer();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 108,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.only(left: 16, top: 8),
        itemCount: 4,
        itemBuilder: (_, __) => Padding(
          padding: const EdgeInsets.only(right: 12),
          child: LoadingShimmer(width: 140, height: 100),
        ),
      ),
    );
  }
}

class _StockTileShimmer extends StatelessWidget {
  const _StockTileShimmer();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          const LoadingShimmer(width: 12, height: 12, borderRadius: 6),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                LoadingShimmer(width: double.infinity, height: 14),
                const SizedBox(height: 6),
                LoadingShimmer(width: 60, height: 12),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              LoadingShimmer(width: 80, height: 14),
              const SizedBox(height: 6),
              LoadingShimmer(width: 56, height: 20, borderRadius: 6),
            ],
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/formatters.dart';
import '../../../../shared/widgets/error_widget.dart';
import '../../../../shared/widgets/loading_shimmer.dart';
import '../../domain/models/portfolio_model.dart';
import '../../domain/portfolio_provider.dart';
import '../widgets/add_position_sheet.dart';
import '../widgets/portfolio_line_tile.dart';

class PortfolioScreen extends ConsumerWidget {
  const PortfolioScreen({super.key});

  void _openAddSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => const AddPositionSheet(),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final portfolioAsync = ref.watch(portfolioProvider);

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        title: const Text('Mon Portefeuille'),
        backgroundColor: AppColors.darkBlue,
        foregroundColor: AppColors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => ref.read(portfolioProvider.notifier).refresh(),
            tooltip: 'Actualiser',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _openAddSheet(context),
        backgroundColor: AppColors.green,
        foregroundColor: AppColors.white,
        child: const Icon(Icons.add),
      ),
      body: portfolioAsync.when(
        loading: _buildLoading,
        error: (e, _) => AkwabaErrorWidget(
          message: 'Impossible de charger le portefeuille.',
          onRetry: () => ref.read(portfolioProvider.notifier).refresh(),
        ),
        data: (portfolio) => _buildContent(context, ref, portfolio),
      ),
    );
  }

  Widget _buildLoading() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: const [
          LoadingShimmer(width: double.infinity, height: 140),
          SizedBox(height: 12),
          LoadingShimmer(width: double.infinity, height: 80),
          SizedBox(height: 8),
          LoadingShimmer(width: double.infinity, height: 80),
          SizedBox(height: 8),
          LoadingShimmer(width: double.infinity, height: 80),
        ],
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    PortfolioModel? portfolio,
  ) {
    final isEmpty = portfolio == null || portfolio.lines.isEmpty;

    return RefreshIndicator(
      color: AppColors.green,
      onRefresh: () => ref.read(portfolioProvider.notifier).refresh(),
      child: isEmpty
          ? _EmptyState(
              screenHeight: MediaQuery.sizeOf(context).height,
            )
          : _PortfolioList(portfolio: portfolio),
    );
  }
}

// ── Empty state ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.screenHeight});

  final double screenHeight;

  @override
  Widget build(BuildContext context) {
    // Wrap in ListView so RefreshIndicator works even when empty.
    return ListView(
      children: [
        SizedBox(
          height: screenHeight - 160,
          child: const Center(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.account_balance_wallet_outlined,
                    size: 64,
                    color: AppColors.greyLine,
                  ),
                  SizedBox(height: 16),
                  Text(
                    'Aucune position',
                    style: TextStyle(
                      color: AppColors.darkBlue,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Ajoutez des actions depuis la fiche action ou appuyez sur +.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.grey, fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ── Portfolio list ────────────────────────────────────────────────────────────

class _PortfolioList extends StatelessWidget {
  const _PortfolioList({required this.portfolio});

  final PortfolioModel portfolio;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        _SummaryCard(portfolio: portfolio),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            'Mes positions (${portfolio.lines.length})',
            style: const TextStyle(
              color: AppColors.darkBlue,
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        ...portfolio.lines.map((line) => PortfolioLineTile(line: line)),
        const SizedBox(height: 80), // space for FAB
      ],
    );
  }
}

// ── Summary card ──────────────────────────────────────────────────────────────

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.portfolio});

  final PortfolioModel portfolio;

  @override
  Widget build(BuildContext context) {
    final gainColor = (portfolio.totalGain ?? 0) >= 0
        ? AppColors.green
        : AppColors.priceDown;

    return Container(
      color: AppColors.darkBlue,
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Valeur totale',
            style: TextStyle(color: Color(0xFF90A4B4), fontSize: 12),
          ),
          const SizedBox(height: 4),
          Text(
            formatFcfa(portfolio.totalValue),
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _SummaryStat(
                label: 'Investi',
                value: formatFcfa(portfolio.totalCost),
                valueColor: AppColors.white,
              ),
              const _SummaryDivider(),
              _SummaryStat(
                label: 'Gain',
                value: formatFcfa(portfolio.totalGain),
                valueColor: gainColor,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _SummaryStat(
                label: 'Performance',
                value: portfolio.totalGainPct != null
                    ? '${portfolio.totalGainPct!.toStringAsFixed(2)}%'
                    : '—',
                valueColor: gainColor,
              ),
              const _SummaryDivider(),
              _SummaryStat(
                label: 'Total Return',
                value: formatFcfa(portfolio.totalReturn),
                valueColor: AppColors.white,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SummaryStat extends StatelessWidget {
  const _SummaryStat({
    required this.label,
    required this.value,
    required this.valueColor,
  });

  final String label;
  final String value;
  final Color valueColor;

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
              fontSize: 11,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              color: valueColor,
              fontSize: 13,
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

class _SummaryDivider extends StatelessWidget {
  const _SummaryDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1,
      height: 32,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      color: const Color(0xFF2D4A5F),
    );
  }
}

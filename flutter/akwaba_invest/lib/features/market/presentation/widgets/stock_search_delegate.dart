import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/providers/market_provider.dart';

/// Custom [SearchDelegate] for stock search.
///
/// Uses [searchResultsProvider] (a [FutureProvider.family]) via a [Consumer]
/// widget inside [buildResults] / [buildSuggestions] so that Riverpod's
/// provider tree is accessible without requiring a [WidgetRef] in the
/// delegate constructor.
///
/// Behaviour:
///   - query < 2 chars → hint message
///   - loading         → centered [CircularProgressIndicator]
///   - no results      → "Aucun résultat pour '…'"
///   - results         → [ListView.builder] of tappable tiles
class StockSearchDelegate extends SearchDelegate<String> {
  @override
  String get searchFieldLabel => 'Rechercher une action…';

  @override
  ThemeData appBarTheme(BuildContext context) {
    final base = Theme.of(context);
    return base.copyWith(
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.darkBlue,
        foregroundColor: AppColors.white,
        elevation: 0,
      ),
      inputDecorationTheme: const InputDecorationTheme(
        border: InputBorder.none,
        hintStyle: TextStyle(color: AppColors.greyLight),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Actions (clear button)
  // ---------------------------------------------------------------------------

  @override
  List<Widget> buildActions(BuildContext context) {
    return [
      if (query.isNotEmpty)
        IconButton(
          icon: const Icon(Icons.clear),
          tooltip: 'Effacer',
          onPressed: () {
            query = '';
            showSuggestions(context);
          },
        ),
    ];
  }

  // ---------------------------------------------------------------------------
  // Leading (back arrow)
  // ---------------------------------------------------------------------------

  @override
  Widget buildLeading(BuildContext context) {
    return IconButton(
      icon: const Icon(Icons.arrow_back),
      tooltip: 'Retour',
      onPressed: () => close(context, ''),
    );
  }

  // ---------------------------------------------------------------------------
  // Results & suggestions share the same widget
  // ---------------------------------------------------------------------------

  @override
  Widget buildResults(BuildContext context) => _buildBody(context);

  @override
  Widget buildSuggestions(BuildContext context) => _buildBody(context);

  Widget _buildBody(BuildContext context) {
    if (query.trim().length < 2) {
      return const Center(
        child: Text(
          'Tapez au moins 2 caractères',
          style: TextStyle(color: AppColors.grey, fontSize: 14),
        ),
      );
    }

    // Consumer gives access to Riverpod providers without storing a ref.
    return Consumer(
      builder: (context, ref, _) {
        final results = ref.watch(searchResultsProvider(query.trim()));

        return results.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (_, __) => const Center(
            child: Text(
              'Erreur lors de la recherche',
              style: TextStyle(color: AppColors.grey),
            ),
          ),
          data: (stocks) {
            if (stocks.isEmpty) {
              return Center(
                child: Text(
                  "Aucun résultat pour '$query'",
                  style: const TextStyle(color: AppColors.grey, fontSize: 14),
                ),
              );
            }

            return ListView.builder(
              itemCount: stocks.length,
              itemBuilder: (_, i) {
                final stock = stocks[i];
                return ListTile(
                  leading: const Icon(Icons.show_chart, color: AppColors.grey),
                  title: Text(
                    stock.name,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text(
                    stock.symbol,
                    style: const TextStyle(color: AppColors.grey),
                  ),
                  onTap: () {
                    close(context, stock.symbol);
                    context.go('/stock/${stock.symbol}');
                  },
                );
              },
            );
          },
        );
      },
    );
  }
}

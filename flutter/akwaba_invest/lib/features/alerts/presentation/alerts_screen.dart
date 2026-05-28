import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/empty_state_widget.dart';
import '../../../shared/widgets/error_widget.dart';
import '../../../shared/widgets/loading_shimmer.dart';
import '../domain/providers/alerts_provider.dart';
import 'widgets/alert_tile.dart';
import 'widgets/create_alert_sheet.dart';

class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alertsState = ref.watch(alertsProvider);

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        title: const Text('Mes Alertes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(alertsProvider.notifier).refresh(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.green,
        onPressed: () => showModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
          ),
          builder: (_) => const CreateAlertSheet(),
        ),
        child: const Icon(Icons.add, color: Colors.white),
      ),
      body: alertsState.when(
        loading: () => ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: 5,
          itemBuilder: (_, __) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: LoadingShimmer(
              width: double.infinity,
              height: 80,
              borderRadius: 12,
            ),
          ),
        ),
        error: (error, _) => AkwabaErrorWidget(
          message: 'Impossible de charger les alertes.',
          onRetry: () => ref.read(alertsProvider.notifier).refresh(),
        ),
        data: (alerts) {
          if (alerts.isEmpty) {
            return EmptyStateWidget(
              icon: Icons.notifications_none_outlined,
              message:
                  'Aucune alerte configurée.\nAppuyez sur + pour créer une alerte de prix.',
            );
          }
          return RefreshIndicator(
            color: AppColors.green,
            onRefresh: () => ref.read(alertsProvider.notifier).refresh(),
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: alerts.length,
              itemBuilder: (context, index) {
                final alert = alerts[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: AlertTile(alert: alert),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

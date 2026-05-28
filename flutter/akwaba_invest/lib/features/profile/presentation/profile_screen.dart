import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../auth/domain/models/app_user.dart';
import '../../auth/domain/providers/auth_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(authProvider);

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        title: const Text('Profil'),
        backgroundColor: AppColors.darkBlue,
        foregroundColor: AppColors.white,
        elevation: 0,
      ),
      body: userAsync.when(
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.green),
        ),
        error: (_, __) => const Center(
          child: Text(
            'Erreur de chargement',
            style: TextStyle(color: AppColors.grey),
          ),
        ),
        data: (user) {
          if (user == null) return const SizedBox.shrink();
          return _buildContent(context, ref, user);
        },
      ),
    );
  }

  Widget _buildContent(BuildContext context, WidgetRef ref, AppUser user) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(user),
          const SizedBox(height: 16),
          _sectionCard('Mon compte', [
            ListTile(
              leading: const Icon(Icons.email_outlined, color: AppColors.grey),
              title: const Text(
                'Adresse e-mail',
                style: TextStyle(fontSize: 13, color: AppColors.grey),
              ),
              subtitle: Text(
                user.email,
                style: const TextStyle(
                  color: AppColors.darkBlue,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.star_outline, color: AppColors.grey),
              title: const Text(
                'Plan',
                style: TextStyle(fontSize: 13, color: AppColors.grey),
              ),
              trailing: _PlanBadge(isPremium: user.isPremium),
            ),
          ]),
          if (!user.isPremium)
            _sectionCard('Abonnement', [
              ListTile(
                leading: const Icon(
                  Icons.workspace_premium_outlined,
                  color: AppColors.orange,
                ),
                title: const Text(
                  'Passer à Premium',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: AppColors.darkBlue,
                  ),
                ),
                subtitle: const Text(
                  '2 000 FCFA/mois · 18 000 FCFA/an',
                  style: TextStyle(fontSize: 12),
                ),
                trailing: const Icon(
                  Icons.arrow_forward_ios,
                  size: 14,
                  color: AppColors.grey,
                ),
                onTap: () {},
              ),
            ]),
          _sectionCard('Actions', [
            ListTile(
              leading: const Icon(Icons.logout, color: AppColors.priceDown),
              title: const Text(
                'Se déconnecter',
                style: TextStyle(
                  color: AppColors.priceDown,
                  fontWeight: FontWeight.w500,
                ),
              ),
              onTap: () => _confirmSignOut(context, ref),
            ),
          ]),
        ],
      ),
    );
  }

  Widget _buildHeader(AppUser user) {
    final displayName = user.displayName;
    final hasName = displayName != null && displayName.isNotEmpty;
    final initial =
        hasName ? displayName[0].toUpperCase() : user.email[0].toUpperCase();
    final name = hasName ? displayName : user.email;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      decoration: BoxDecoration(
        color: AppColors.darkBlue,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          CircleAvatar(
            radius: 36,
            backgroundColor: AppColors.green,
            child: Text(
              initial,
              style: const TextStyle(
                color: AppColors.white,
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            name,
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (hasName) ...[
            const SizedBox(height: 4),
            Text(
              user.email,
              style: const TextStyle(
                color: Color(0xFF90A4B4),
                fontSize: 13,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _confirmSignOut(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Déconnexion'),
        content:
            const Text('Êtes-vous sûr de vouloir vous déconnecter ?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.priceDown,
            ),
            child: const Text('Déconnecter'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await ref.read(authProvider.notifier).signOut();
    }
  }

  Widget _sectionCard(String title, List<Widget> tiles) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
                color: AppColors.darkBlue,
              ),
            ),
          ),
          const Divider(height: 1),
          ...tiles,
        ],
      ),
    );
  }
}

// ── Plan badge ────────────────────────────────────────────────────────────────

class _PlanBadge extends StatelessWidget {
  const _PlanBadge({required this.isPremium});

  final bool isPremium;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: isPremium
            ? AppColors.orange.withValues(alpha: 0.15)
            : AppColors.greyLight,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isPremium ? AppColors.orange : AppColors.greyLine,
        ),
      ),
      child: Text(
        isPremium ? 'Premium' : 'Gratuit',
        style: TextStyle(
          color: isPremium ? AppColors.orange : AppColors.grey,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    );
  }
}

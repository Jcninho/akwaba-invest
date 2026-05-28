import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/portfolio_provider.dart';

/// Modal bottom sheet for adding a new portfolio position.
///
/// [prefilledSymbol] is set when opened from a stock detail screen.
class AddPositionSheet extends ConsumerStatefulWidget {
  const AddPositionSheet({super.key, this.prefilledSymbol});

  final String? prefilledSymbol;

  @override
  ConsumerState<AddPositionSheet> createState() => _AddPositionSheetState();
}

class _AddPositionSheetState extends ConsumerState<AddPositionSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _symbolCtrl;
  final _quantityCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _symbolCtrl = TextEditingController(text: widget.prefilledSymbol ?? '');
  }

  @override
  void dispose() {
    _symbolCtrl.dispose();
    _quantityCtrl.dispose();
    _priceCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final symbol = _symbolCtrl.text.trim().toUpperCase();
    final quantity =
        double.parse(_quantityCtrl.text.trim().replaceAll(',', '.'));
    final price = double.parse(_priceCtrl.text.trim().replaceAll(',', '.'));

    setState(() => _isLoading = true);
    try {
      await ref.read(portfolioProvider.notifier).addLine(symbol, quantity, price);
      if (!mounted) return;
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Position ajoutée'),
          backgroundColor: AppColors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erreur : $e'),
          backgroundColor: AppColors.priceDown,
        ),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        top: 16,
        left: 16,
        right: 16,
        bottom: MediaQuery.viewInsetsOf(context).bottom + 24,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Handle bar
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.greyLine,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Ajouter une position',
              style: TextStyle(
                color: AppColors.darkBlue,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),
            // Symbole
            TextFormField(
              controller: _symbolCtrl,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                labelText: 'Symbole',
                hintText: 'ex: SNTS',
                border: OutlineInputBorder(),
              ),
              validator: (v) {
                final s = v?.trim() ?? '';
                if (s.isEmpty) return 'Champ requis';
                if (s.length < 2 || s.length > 6) return '2 à 6 caractères';
                return null;
              },
            ),
            const SizedBox(height: 12),
            // Quantité
            TextFormField(
              controller: _quantityCtrl,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Quantité',
                border: OutlineInputBorder(),
              ),
              validator: (v) {
                final n = double.tryParse(v?.replaceAll(',', '.') ?? '');
                if (n == null || n <= 0) return 'Quantité invalide (> 0)';
                return null;
              },
            ),
            const SizedBox(height: 12),
            // Prix d'achat
            TextFormField(
              controller: _priceCtrl,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: "Prix d'achat (FCFA)",
                border: OutlineInputBorder(),
              ),
              validator: (v) {
                final n = double.tryParse(v?.replaceAll(',', '.') ?? '');
                if (n == null || n <= 0) return 'Prix invalide (> 0)';
                return null;
              },
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _submit,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.green,
                  foregroundColor: AppColors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          color: AppColors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : const Text(
                        'Ajouter',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

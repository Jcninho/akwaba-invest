import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/providers/alerts_provider.dart';

class CreateAlertSheet extends ConsumerStatefulWidget {
  const CreateAlertSheet({super.key, this.prefilledSymbol});

  final String? prefilledSymbol;

  @override
  ConsumerState<CreateAlertSheet> createState() => _CreateAlertSheetState();
}

class _CreateAlertSheetState extends ConsumerState<CreateAlertSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _symbolCtrl;
  final _thresholdCtrl = TextEditingController();
  String _alertType = 'price_above';
  bool _isLoading = false;

  static const _alertTypeOptions = [
    ('price_above', 'Hausse au-dessus de'),
    ('price_below', 'Baisse sous'),
    ('dividend', 'Nouveau dividende'),
  ];

  bool get _isPriceAlert => _alertType != 'dividend';

  @override
  void initState() {
    super.initState();
    _symbolCtrl = TextEditingController(text: widget.prefilledSymbol ?? '');
  }

  @override
  void dispose() {
    _symbolCtrl.dispose();
    _thresholdCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final symbol = _symbolCtrl.text.trim().toUpperCase();
    final threshold = _isPriceAlert
        ? double.parse(_thresholdCtrl.text.trim().replaceAll(',', '.'))
        : null;

    setState(() => _isLoading = true);
    try {
      await ref.read(alertsProvider.notifier).createAlert(
            symbol: symbol,
            alertType: _alertType,
            threshold: threshold,
          );
      if (!mounted) return;
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Alerte créée'),
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
              'Créer une alerte',
              style: TextStyle(
                color: AppColors.darkBlue,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 20),
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
            DropdownButtonFormField<String>(
              initialValue: _alertType,
              decoration: const InputDecoration(
                labelText: "Type d'alerte",
                border: OutlineInputBorder(),
              ),
              items: _alertTypeOptions
                  .map(
                    (opt) => DropdownMenuItem<String>(
                      value: opt.$1,
                      child: Text(opt.$2),
                    ),
                  )
                  .toList(),
              onChanged: (val) {
                if (val != null) setState(() => _alertType = val);
              },
            ),
            if (_isPriceAlert) ...[
              const SizedBox(height: 12),
              TextFormField(
                controller: _thresholdCtrl,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Seuil (FCFA)',
                  border: OutlineInputBorder(),
                ),
                validator: (v) {
                  if (!_isPriceAlert) return null;
                  final n = double.tryParse(v?.replaceAll(',', '.') ?? '');
                  if (n == null || n <= 0) return 'Seuil invalide (> 0)';
                  return null;
                },
              ),
            ],
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
                        "Créer l'alerte",
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

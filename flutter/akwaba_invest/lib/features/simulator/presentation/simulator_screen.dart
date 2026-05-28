import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/formatters.dart';
import '../domain/simulator_provider.dart';

class SimulatorScreen extends ConsumerStatefulWidget {
  const SimulatorScreen({super.key});

  @override
  ConsumerState<SimulatorScreen> createState() => _SimulatorScreenState();
}

class _SimulatorScreenState extends ConsumerState<SimulatorScreen> {
  late final TextEditingController _amountCtrl;
  late final TextEditingController _priceCtrl;
  late final TextEditingController _dividendCtrl;

  @override
  void initState() {
    super.initState();
    const d = SimulatorState();
    _amountCtrl = TextEditingController(text: d.amount.toInt().toString());
    _priceCtrl = TextEditingController(text: d.price.toInt().toString());
    _dividendCtrl =
        TextEditingController(text: d.dividendPerShare.toInt().toString());
  }

  @override
  void dispose() {
    _amountCtrl.dispose();
    _priceCtrl.dispose();
    _dividendCtrl.dispose();
    super.dispose();
  }

  void _reset() {
    ref.read(simulatorProvider.notifier).reset();
    const d = SimulatorState();
    _amountCtrl.text = d.amount.toInt().toString();
    _priceCtrl.text = d.price.toInt().toString();
    _dividendCtrl.text = d.dividendPerShare.toInt().toString();
  }

  double? _parse(String text) {
    final n = double.tryParse(text.trim().replaceAll(',', '.'));
    return (n != null && n > 0) ? n : null;
  }

  @override
  Widget build(BuildContext context) {
    final sim = ref.watch(simulatorProvider);

    return Scaffold(
      backgroundColor: AppColors.scaffold,
      appBar: AppBar(
        title: const Text('Simulateur'),
        backgroundColor: AppColors.darkBlue,
        foregroundColor: AppColors.white,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.restore_outlined),
            onPressed: _reset,
            tooltip: 'Réinitialiser',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildParamCard(sim),
            const SizedBox(height: 16),
            _buildResultsCard(sim),
            const SizedBox(height: 16),
            _buildDisclaimer(),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildParamCard(SimulatorState sim) {
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
            const Text(
              'Paramètres',
              style: TextStyle(
                color: AppColors.darkBlue,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            const Divider(color: AppColors.greyLine),
            const SizedBox(height: 8),

            // Montant
            TextFormField(
              controller: _amountCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Montant (FCFA)',
                suffixText: 'FCFA',
                border: OutlineInputBorder(),
              ),
              onChanged: (v) {
                final n = _parse(v);
                if (n != null) ref.read(simulatorProvider.notifier).updateAmount(n);
              },
            ),
            const SizedBox(height: 12),

            // Cours
            TextFormField(
              controller: _priceCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Cours actuel (FCFA)',
                border: OutlineInputBorder(),
              ),
              onChanged: (v) {
                final n = _parse(v);
                if (n != null) ref.read(simulatorProvider.notifier).updatePrice(n);
              },
            ),
            const SizedBox(height: 12),

            // Dividende
            TextFormField(
              controller: _dividendCtrl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Dividende net (FCFA/action)',
                border: OutlineInputBorder(),
              ),
              onChanged: (v) {
                final n = _parse(v);
                if (n != null) {
                  ref.read(simulatorProvider.notifier).updateDividend(n);
                }
              },
            ),
            const SizedBox(height: 16),

            // Croissance (slider)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Croissance annuelle (%)',
                  style: TextStyle(color: AppColors.grey, fontSize: 13),
                ),
                Text(
                  '${sim.annualGrowth.toStringAsFixed(1)}%',
                  style: const TextStyle(
                    color: AppColors.darkBlue,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
            Slider(
              value: sim.annualGrowth,
              min: 0,
              max: 30,
              divisions: 60,
              activeColor: AppColors.green,
              onChanged: (v) =>
                  ref.read(simulatorProvider.notifier).updateGrowth(v),
            ),
            const SizedBox(height: 8),

            // Durée (chips)
            const Text(
              'Durée (années)',
              style: TextStyle(color: AppColors.grey, fontSize: 13),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [1, 3, 5, 10, 20].map((year) {
                final selected = sim.years == year;
                return GestureDetector(
                  onTap: () =>
                      ref.read(simulatorProvider.notifier).updateYears(year),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      color: selected ? AppColors.green : AppColors.greyLight,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      '$year an${year > 1 ? 's' : ''}',
                      style: TextStyle(
                        color: selected ? AppColors.white : AppColors.grey,
                        fontWeight:
                            selected ? FontWeight.w600 : FontWeight.normal,
                        fontSize: 13,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultsCard(SimulatorState sim) {
    final fv = sim.futureValue;
    final gain = sim.totalGain;
    final gainPct = sim.totalGainPct;
    final shares = sim.shares;
    final annualDiv = sim.annualDividendTotal;
    final yieldPct = sim.dividendYieldPct;

    return Container(
      decoration: BoxDecoration(
        color: AppColors.darkBlue,
        borderRadius: BorderRadius.circular(12),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Résultats estimés',
            style: TextStyle(
              color: AppColors.white,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Divider(color: AppColors.white.withValues(alpha: 0.2)),
          const SizedBox(height: 12),

          // Valeur future — large
          const Text(
            'Valeur future',
            style: TextStyle(color: Color(0xFF90A4B4), fontSize: 12),
          ),
          const SizedBox(height: 4),
          Text(
            fv.isFinite ? formatFcfa(fv.round()) : '—',
            style: const TextStyle(
              color: AppColors.white,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),

          // Grid 2×2
          Row(
            children: [
              Expanded(
                child: _ResultCell(
                  label: "Nombre d'actions",
                  value: shares.isFinite && shares > 0
                      ? '${shares.toStringAsFixed(1)} titres'
                      : '—',
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ResultCell(
                  label: 'Gain total',
                  value: gain.isFinite ? formatFcfa(gain.round()) : '—',
                  valueColor: AppColors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _ResultCell(
                  label: 'Performance',
                  value: gainPct.isFinite
                      ? '${gainPct.toStringAsFixed(1)}%'
                      : '—',
                  valueColor: AppColors.green,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _ResultCell(
                  label: 'Dividende annuel',
                  value:
                      annualDiv.isFinite ? formatFcfa(annualDiv.round()) : '—',
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Rendement dividende
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.white.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Rendement dividende',
                  style: TextStyle(color: Color(0xFF90A4B4), fontSize: 13),
                ),
                Text(
                  yieldPct > 0 && yieldPct.isFinite
                      ? '${yieldPct.toStringAsFixed(2)}%'
                      : '—',
                  style: const TextStyle(
                    color: AppColors.green,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDisclaimer() {
    return const Padding(
      padding: EdgeInsets.symmetric(horizontal: 4),
      child: Text(
        'Les simulations sont fournies à titre indicatif uniquement et ne constituent pas un conseil en investissement.',
        textAlign: TextAlign.center,
        style: TextStyle(
          color: AppColors.grey,
          fontSize: 11,
          height: 1.5,
        ),
      ),
    );
  }
}

// ── Result cell widget ────────────────────────────────────────────────────────

class _ResultCell extends StatelessWidget {
  const _ResultCell({
    required this.label,
    required this.value,
    this.valueColor,
  });

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E3A50),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(color: Color(0xFF90A4B4), fontSize: 11),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? AppColors.white,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

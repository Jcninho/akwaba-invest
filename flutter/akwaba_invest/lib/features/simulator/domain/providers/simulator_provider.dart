import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Input state for the investment simulator.
class SimulatorInput {
  const SimulatorInput({
    this.symbol = '',
    this.initialAmount = 0.0,
    this.monthlyAmount = 0.0,
    this.years = 5,
  });

  final String symbol;
  final double initialAmount;
  final double monthlyAmount;
  final int years;
}

final simulatorInputProvider =
    StateNotifierProvider<SimulatorInputNotifier, SimulatorInput>(
  (ref) => SimulatorInputNotifier(),
);

class SimulatorInputNotifier extends StateNotifier<SimulatorInput> {
  SimulatorInputNotifier() : super(const SimulatorInput());

  void update({
    String? symbol,
    double? initialAmount,
    double? monthlyAmount,
    int? years,
  }) {
    state = SimulatorInput(
      symbol: symbol ?? state.symbol,
      initialAmount: initialAmount ?? state.initialAmount,
      monthlyAmount: monthlyAmount ?? state.monthlyAmount,
      years: years ?? state.years,
    );
  }
}

/// Computed simulation result derived from [simulatorInputProvider].
/// TODO: implement projection calculation (compound growth, dividends reinvested)
final simulatorResultProvider = Provider<dynamic>((ref) {
  ref.watch(simulatorInputProvider);
  return null;
});

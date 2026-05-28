import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';

class SimulatorState {
  final double amount;
  final double price;
  final double dividendPerShare;
  final double annualGrowth;
  final int years;

  double get shares => amount / price;
  double get annualDividendTotal => shares * dividendPerShare;
  double get dividendYieldPct =>
      price > 0 ? (dividendPerShare / price) * 100 : 0;
  double get futureValue =>
      amount * pow(1 + annualGrowth / 100, years).toDouble();
  double get totalGain => futureValue - amount;
  double get totalGainPct =>
      amount > 0 ? ((futureValue - amount) / amount) * 100 : 0;

  const SimulatorState({
    this.amount = 500000,
    this.price = 28900,
    this.dividendPerShare = 1655,
    this.annualGrowth = 8,
    this.years = 5,
  });

  SimulatorState copyWith({
    double? amount,
    double? price,
    double? dividendPerShare,
    double? annualGrowth,
    int? years,
  }) =>
      SimulatorState(
        amount: amount ?? this.amount,
        price: price ?? this.price,
        dividendPerShare: dividendPerShare ?? this.dividendPerShare,
        annualGrowth: annualGrowth ?? this.annualGrowth,
        years: years ?? this.years,
      );
}

final simulatorProvider =
    StateNotifierProvider<SimulatorNotifier, SimulatorState>(
  (ref) => SimulatorNotifier(),
);

class SimulatorNotifier extends StateNotifier<SimulatorState> {
  SimulatorNotifier() : super(const SimulatorState());

  void updateAmount(double value) => state = state.copyWith(amount: value);
  void updatePrice(double value) => state = state.copyWith(price: value);
  void updateDividend(double value) =>
      state = state.copyWith(dividendPerShare: value);
  void updateGrowth(double value) =>
      state = state.copyWith(annualGrowth: value);
  void updateYears(int value) => state = state.copyWith(years: value);
  void reset() => state = const SimulatorState();
}

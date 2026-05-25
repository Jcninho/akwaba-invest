import 'package:flutter/material.dart';

class StockDetailScreen extends StatelessWidget {
  const StockDetailScreen({super.key, required this.symbol});

  final String symbol;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(symbol)),
      body: const Center(child: Text('TODO')),
    );
  }
}

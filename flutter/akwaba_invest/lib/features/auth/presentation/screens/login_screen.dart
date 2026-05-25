import 'package:flutter/material.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A2E40),
      appBar: AppBar(
        title: const Text('Akwaba Invest'),
        backgroundColor: const Color(0xFF1A2E40),
      ),
      body: const Center(
        child: Text(
          'TODO: Login screen',
          style: TextStyle(color: Colors.white),
        ),
      ),
    );
  }
}

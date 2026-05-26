import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/providers/auth_provider.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  /// True while the registration request is in flight (local UI state only).
  bool _registering = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Action
  // ---------------------------------------------------------------------------

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _registering = true);

    await ref.read(authProvider.notifier).register(
          _emailController.text.trim(),
          _passwordController.text,
        );

    if (!mounted) return;
    setState(() => _registering = false);

    // On success the router redirect handles navigation to /market.
    // On failure show a snackbar.
    final authState = ref.read(authProvider);
    authState.whenOrNull(
      error: (error, _) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(_errorMessage(error)),
            backgroundColor: Colors.red[700],
            behavior: SnackBarBehavior.floating,
          ),
        );
      },
    );
  }

  String _errorMessage(Object error) {
    if (error is FirebaseAuthException) {
      return switch (error.code) {
        'email-already-in-use' => 'Un compte existe déjà pour cet email.',
        'invalid-email' => 'Adresse email invalide.',
        'weak-password' => 'Mot de passe trop faible (minimum 6 caractères).',
        'operation-not-allowed' => 'Création de compte désactivée.',
        _ => 'Erreur lors de la création du compte. Réessayez.',
      };
    }
    return 'Erreur lors de la création du compte. Réessayez.';
  }

  // ---------------------------------------------------------------------------
  // Validators
  // ---------------------------------------------------------------------------

  String? _validateEmail(String? value) {
    if (value == null || value.trim().isEmpty) return 'Email requis';
    if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value.trim())) {
      return 'Email invalide';
    }
    return null;
  }

  String? _validatePassword(String? value) {
    if (value == null || value.isEmpty) return 'Mot de passe requis';
    if (value.length < 6) return 'Minimum 6 caractères';
    return null;
  }

  String? _validateConfirm(String? value) {
    if (value == null || value.isEmpty) return 'Confirmation requise';
    if (value != _passwordController.text) {
      return 'Les mots de passe ne correspondent pas';
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.scaffold,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            children: [
              const SizedBox(height: 32),

              // ── Logo / Title ──────────────────────────────────────────────
              const Text(
                'Akwaba Invest',
                style: TextStyle(
                  color: AppColors.darkBlue,
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Créer un compte',
                style: TextStyle(
                  color: AppColors.grey,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 40),

              // ── Form card ─────────────────────────────────────────────────
              Container(
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x14000000),
                      blurRadius: 16,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                padding: const EdgeInsets.all(24),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Email
                      TextFormField(
                        controller: _emailController,
                        keyboardType: TextInputType.emailAddress,
                        textInputAction: TextInputAction.next,
                        decoration: const InputDecoration(
                          labelText: 'Email',
                          prefixIcon: Icon(Icons.email_outlined),
                        ),
                        validator: _validateEmail,
                      ),
                      const SizedBox(height: 16),

                      // Password
                      TextFormField(
                        controller: _passwordController,
                        obscureText: _obscurePassword,
                        textInputAction: TextInputAction.next,
                        decoration: InputDecoration(
                          labelText: 'Mot de passe',
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                            ),
                            onPressed: () => setState(
                              () => _obscurePassword = !_obscurePassword,
                            ),
                          ),
                        ),
                        validator: _validatePassword,
                      ),
                      const SizedBox(height: 16),

                      // Confirm password
                      TextFormField(
                        controller: _confirmPasswordController,
                        obscureText: _obscureConfirm,
                        textInputAction: TextInputAction.done,
                        onFieldSubmitted: (_) => _register(),
                        decoration: InputDecoration(
                          labelText: 'Confirmer le mot de passe',
                          prefixIcon: const Icon(Icons.lock_outline),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureConfirm
                                  ? Icons.visibility_outlined
                                  : Icons.visibility_off_outlined,
                            ),
                            onPressed: () => setState(
                              () => _obscureConfirm = !_obscureConfirm,
                            ),
                          ),
                        ),
                        validator: _validateConfirm,
                      ),
                      const SizedBox(height: 24),

                      // Register button
                      SizedBox(
                        height: 48,
                        child: ElevatedButton(
                          onPressed: _registering ? null : _register,
                          child: _registering
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppColors.white,
                                  ),
                                )
                              : const Text('Créer mon compte'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 28),

              // ── Login link ────────────────────────────────────────────────
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text(
                    'Déjà un compte ? ',
                    style: TextStyle(color: AppColors.grey),
                  ),
                  GestureDetector(
                    onTap: () => context.go('/login'),
                    child: const Text(
                      'Se connecter',
                      style: TextStyle(
                        color: AppColors.green,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

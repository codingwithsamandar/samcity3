import 'package:flutter/material.dart';

import '../theme.dart';

/// Bo'sh holat ko'rsatkichi — ikonka, sarlavha, ixtiyoriy izoh va harakat tugmasi.
///
/// Butun ilova bo'ylab bir xil ko'rinishdagi «bo'sh ro'yxat» holati uchun.
/// RefreshIndicator ichida pull-to-refresh ishlashi uchun `.scrollable()` bilan
/// ListView'ga o'raladi.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String? subtitle;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: const BoxDecoration(
                color: AppTheme.surface2Dark,
                shape: BoxShape.circle,
              ),
              child: Icon(icon, size: 40, color: AppTheme.text2Dark),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 17, fontWeight: FontWeight.w800, color: AppTheme.textDark),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 6),
              Text(
                subtitle!,
                textAlign: TextAlign.center,
                style: const TextStyle(
                    fontSize: 14, color: AppTheme.text2Dark, height: 1.4),
              ),
            ],
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 20),
              FilledButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }

  /// Pull-to-refresh (RefreshIndicator) ichida ishlashi uchun scroll-do'st variant.
  Widget scrollable() => ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [const SizedBox(height: 72), this],
      );
}

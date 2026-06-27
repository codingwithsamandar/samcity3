import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router.dart';
import 'core/theme.dart';

void main() {
  runApp(const ProviderScope(child: SamCityApp()));
}

class SamCityApp extends ConsumerWidget {
  const SamCityApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    return MaterialApp.router(
      title: 'SamCity',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark(),
      routerConfig: router,
      builder: (context, child) {
        // Web/keng ekranда ilovani telefon kengligida (markazda) ko'rsatamiz —
        // aks holda hamma narsa cho'zilib, "buzuq" ko'rinadi.
        final mq = MediaQuery.of(context);
        if (mq.size.width <= 600 || child == null) return child ?? const SizedBox();
        const phoneW = 430.0;
        return ColoredBox(
          color: const Color(0xFF05080D),
          child: Center(
            child: SizedBox(
              width: phoneW,
              child: MediaQuery(
                // Bola ekranlar layoutni telefon kengligiga qarab hisoblasin
                data: mq.copyWith(size: Size(phoneW, mq.size.height)),
                child: ClipRect(child: child),
              ),
            ),
          ),
        );
      },
    );
  }
}

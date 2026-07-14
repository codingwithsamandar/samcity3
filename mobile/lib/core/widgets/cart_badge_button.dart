import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers.dart';

/// Savat ikonkasi + jonli badge (mahsulot soni). Bosilganda savatga o'tadi.
///
/// Savatga mahsulot qo'shilganda son o'zgaradi va badge «pop» qilib bildiradi —
/// foydalanuvchi mahsulot savatga tushganini aniq ko'radi.
class CartBadgeButton extends ConsumerWidget {
  const CartBadgeButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final count = ref.watch(cartControllerProvider.select((c) => c.totalQuantity));
    return IconButton(
      tooltip: 'Savat',
      onPressed: () => context.push('/cart'),
      icon: TweenAnimationBuilder<double>(
        // key = count → har o'zgarishda animatsiya qayta boshlanadi (pop effekti).
        key: ValueKey(count),
        tween: Tween(begin: count > 0 ? 0.55 : 1.0, end: 1.0),
        duration: const Duration(milliseconds: 280),
        curve: Curves.elasticOut,
        builder: (_, scale, child) => Transform.scale(scale: scale, child: child),
        child: Badge(
          isLabelVisible: count > 0,
          label: Text('$count'),
          backgroundColor: const Color(0xFF34D399),
          textColor: const Color(0xFF06211F),
          child: const Icon(Icons.shopping_cart_outlined),
        ),
      ),
    );
  }
}

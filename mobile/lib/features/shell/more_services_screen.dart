import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Qo'shimcha xizmatlar — bottom nav "Ko'proq" tabi.
class MoreServicesScreen extends StatelessWidget {
  const MoreServicesScreen({super.key});

  static const _items = [
    _ServiceItem(Icons.location_city, 'Joylar', "To'yxona, restoran, salon", '/venues', Color(0xFF34D399)),
    _ServiceItem(Icons.work_outline, 'Ish e\'lonlari', 'Vakansiya va rezyume', '/jobs', Color(0xFFCAA23A)),
    _ServiceItem(Icons.groups_outlined, 'Mahalla', "So'rovnoma va yordam", '/community', Color(0xFF22D3EE)),
    _ServiceItem(Icons.receipt_long_outlined, 'To\'lovlar', 'Kommunal, kurs, bog\'cha', '/service-payments', Color(0xFF34D399)),
    _ServiceItem(Icons.map_outlined, 'Xarita', 'Do\'kon va muassasalar', '/map', Color(0xFF22D3EE)),
    _ServiceItem(Icons.event_note_outlined, 'Bronlarim', 'Joy bronlari', '/my-bookings', Color(0xFFCAA23A)),
    _ServiceItem(Icons.local_taxi_outlined, 'Sayohatlarim', 'Taksi tarixi', '/trips', Color(0xFF69748A)),
    _ServiceItem(Icons.shopping_bag_outlined, 'Buyurtmalarim', 'Yetkazish buyurtmalari', '/orders', Color(0xFF34D399)),
    _ServiceItem(Icons.storefront_outlined, 'Do\'konlarim', 'Biznes paneli', '/my-stores', Color(0xFF22D3EE)),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Xizmatlar')),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          childAspectRatio: 1.15,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
        ),
        itemCount: _items.length,
        itemBuilder: (_, i) {
          final item = _items[i];
          return Material(
            color: const Color(0xFF141B29),
            borderRadius: BorderRadius.circular(16),
            child: InkWell(
              onTap: () => context.push(item.route),
              borderRadius: BorderRadius.circular(16),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(item.icon, color: item.color, size: 28),
                    const Spacer(),
                    Text(item.title,
                        style: const TextStyle(
                            fontWeight: FontWeight.w800, fontSize: 14)),
                    const SizedBox(height: 4),
                    Text(item.subtitle,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                            fontSize: 11, color: Color(0xFF69748A))),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ServiceItem {
  const _ServiceItem(this.icon, this.title, this.subtitle, this.route, this.color);
  final IconData icon;
  final String title;
  final String subtitle;
  final String route;
  final Color color;
}

// SamCity — asosiy birlik testlari.
//
// To'liq ilovani (SamCityApp) test qilish flutter_secure_storage kabi
// platforma plaginlarini talab qiladi, shuning uchun bu yerda plaginsiz,
// sof-Dart mantiq (narx formatlash, model parsing) tekshiriladi.

import 'package:flutter_test/flutter_test.dart';

import 'package:samcity/features/delivery/delivery_models.dart';
import 'package:samcity/features/ads/ad_model.dart';

void main() {
  group('money() formatlash', () {
    test('minglarni bo\'sh joy bilan ajratadi', () {
      expect(money(1000), '1 000');
      expect(money(1234567), '1 234 567');
    });

    test('kichik sonlar o\'zgarmaydi', () {
      expect(money(0), '0');
      expect(money(999), '999');
    });
  });

  group('AdListItem.fromJson', () {
    test('to\'liq JSON to\'g\'ri o\'qiladi', () {
      final ad = AdListItem.fromJson({
        'id': 42,
        'title': 'Velosiped',
        'price': 500000,
        'price_type': 'fixed',
        'category': 'transport',
        'category_display': 'Transport',
        'location': 'Samarqand',
        'is_boosted': true,
        'views': 12,
      });
      expect(ad.id, '42');
      expect(ad.title, 'Velosiped');
      expect(ad.price, 500000);
      expect(ad.isBoosted, true);
      expect(ad.priceLabel, "500 000 so'm");
    });

    test('yetishmayotgan maydonlar xavfsiz standart qiymat oladi', () {
      final ad = AdListItem.fromJson({'id': 1});
      expect(ad.title, '');
      expect(ad.price, isNull);
      expect(ad.priceType, 'fixed');
      expect(ad.isBoosted, false);
      expect(ad.views, 0);
    });

    test('bepul e\'lon narxi to\'g\'ri belgilanadi', () {
      final ad = AdListItem.fromJson({'id': 1, 'price_type': 'free'});
      expect(ad.priceLabel, 'Bepul');
    });
  });
}

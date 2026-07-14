import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Telefon raqamiga qo'ng'iroq qiladi (tel:). Ortiqcha belgilarni tozalaydi.
Future<void> callPhone(BuildContext context, String phone) async {
  final clean = phone.replaceAll(RegExp(r'[^0-9+]'), '');
  if (clean.isEmpty) return;
  try {
    final ok = await launchUrl(Uri.parse('tel:$clean'),
        mode: LaunchMode.externalApplication);
    if (!ok && context.mounted) _fail(context, phone);
  } catch (_) {
    if (context.mounted) _fail(context, phone);
  }
}

void _fail(BuildContext context, String phone) {
  ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Qo'ng'iroq qilib bo'lmadi: $phone")));
}

/// Bosiladigan telefon raqami — bosilganda qo'ng'iroq qiladi (yashil, ikonkali).
class PhoneLink extends StatelessWidget {
  const PhoneLink(this.phone, {super.key, this.style, this.showIcon = true});
  final String phone;
  final TextStyle? style;
  final bool showIcon;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => callPhone(context, phone),
      borderRadius: BorderRadius.circular(6),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 3, horizontal: 2),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showIcon) ...[
              const Icon(Icons.phone, size: 15, color: Color(0xFF34D399)),
              const SizedBox(width: 5),
            ],
            Flexible(
              child: Text(
                phone,
                style: (style ?? const TextStyle()).copyWith(
                  color: const Color(0xFF34D399),
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

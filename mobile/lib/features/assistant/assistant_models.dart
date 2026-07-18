// AI yordamchi javob modellari — backend `/api/assistant/chat/` bilan mos.
// Web widget va mobil ilova aynan bir xil JSON qaytaradi.

/// Joy kartasi (dorixona, shifoxona, bank va h.k.).
class AiCard {
  final String title;
  final String subtitle;
  final String icon;
  final String? distance; // "102 m"
  final String? walk; // "🚶 ~1 daq"
  final bool? open; // true/false/null (noma'lum)
  final String? phone;
  final String? routeUrl; // Google Maps yo'nalish
  final double? lat;
  final double? lng;

  const AiCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    this.distance,
    this.walk,
    this.open,
    this.phone,
    this.routeUrl,
    this.lat,
    this.lng,
  });

  factory AiCard.fromJson(Map<String, dynamic> j) => AiCard(
        title: (j['title'] ?? '').toString(),
        subtitle: (j['subtitle'] ?? '').toString(),
        icon: (j['icon'] ?? '📍').toString(),
        distance: j['distance']?.toString(),
        walk: j['walk']?.toString(),
        open: j['open'] is bool ? j['open'] as bool : null,
        phone: (j['phone']?.toString().isNotEmpty ?? false) ? j['phone'].toString() : null,
        routeUrl: (j['route_url']?.toString().isNotEmpty ?? false) ? j['route_url'].toString() : null,
        lat: (j['lat'] is num) ? (j['lat'] as num).toDouble() : null,
        lng: (j['lng'] is num) ? (j['lng'] as num).toDouble() : null,
      );
}

/// Tez amal tugmasi: `q` bo'lsa — savol yuboradi, `url` bo'lsa — web'da ochadi.
class AiAction {
  final String label;
  final String? q; // yangi savol (masalan "yana dorixona")
  final String? url; // web sahifa (masalan "/map/directory/?...")

  const AiAction({required this.label, this.q, this.url});

  factory AiAction.fromJson(Map<String, dynamic> j) => AiAction(
        label: (j['label'] ?? '').toString(),
        q: (j['q']?.toString().isNotEmpty ?? false) ? j['q'].toString() : null,
        url: (j['url']?.toString().isNotEmpty ?? false) ? j['url'].toString() : null,
      );
}

/// Yordamchi to'liq javobi.
class AiResponse {
  final String reply;
  final List<AiCard> cards;
  final List<AiAction> actions;
  final String? category; // "yana" konteksti uchun
  final int nextOffset;

  const AiResponse({
    required this.reply,
    this.cards = const [],
    this.actions = const [],
    this.category,
    this.nextOffset = 0,
  });

  factory AiResponse.fromJson(Map<String, dynamic> j) => AiResponse(
        reply: (j['reply'] ?? 'Kechirasiz, javob berolmadim.').toString(),
        cards: ((j['cards'] as List?) ?? [])
            .whereType<Map>()
            .map((e) => AiCard.fromJson(e.cast<String, dynamic>()))
            .toList(),
        actions: ((j['actions'] as List?) ?? [])
            .whereType<Map>()
            .map((e) => AiAction.fromJson(e.cast<String, dynamic>()))
            .toList(),
        category: j['category']?.toString(),
        nextOffset: (j['next_offset'] is num) ? (j['next_offset'] as num).toInt() : 0,
      );
}

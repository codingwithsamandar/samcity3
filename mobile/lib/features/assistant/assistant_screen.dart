import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/config.dart';
import '../../core/dialer.dart';
import '../../core/providers.dart';
import 'assistant_models.dart';

/// AI yordamchi chat ekrani — web widget bilan bir xil oqim.
/// Savol yozing → mahalliy dvigatel eng yaqin joyni topib beradi (kartalar,
/// masofa, ochiq/yopiq, qo'ng'iroq, yo'nalish). Joylashuvni ulash aniqroq qiladi.
class AssistantScreen extends ConsumerStatefulWidget {
  const AssistantScreen({super.key});

  @override
  ConsumerState<AssistantScreen> createState() => _AssistantScreenState();
}

/// Suhbat elementi: foydalanuvchi/yordamchi xabari, kartalar yoki amallar.
sealed class _Item {}

class _Msg extends _Item {
  _Msg(this.text, {required this.mine});
  final String text;
  final bool mine;
}

class _Cards extends _Item {
  _Cards(this.cards);
  final List<AiCard> cards;
}

class _Actions extends _Item {
  _Actions(this.actions);
  final List<AiAction> actions;
}

class _AssistantScreenState extends ConsumerState<AssistantScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<_Item> _items = [];
  final List<Map<String, String>> _history = [];

  // Suhbat konteksti ("yana" va follow-up uchun) — web bilan bir xil.
  Map<String, dynamic> _ctx = {'last_category': null, 'offset': 0};
  double? _lat, _lng;
  bool _busy = false;
  bool _locating = false;

  static const _chips = [
    ('💊 Dorixona', 'Eng yaqin dorixona qayerda'),
    ('🏥 Shifoxona', 'Eng yaqin shifoxona'),
    ('🏦 Bank', 'Yaqin bank'),
    ('🍽️ Restoran', 'Yaqin restoran'),
    ('🚗 Taksi', 'Taksi chaqirish'),
  ];

  @override
  void initState() {
    super.initState();
    final h = DateTime.now().hour;
    final greet = h < 5
        ? 'Xayrli tun'
        : h < 11
            ? 'Xayrli tong'
            : h < 18
                ? 'Xayrli kun'
                : 'Xayrli kech';
    _items.add(_Msg(
      "$greet! 👋 Men SamCity yordamchisiman. Eng yaqin dorixona, shifoxona, "
      "bank yoki restoranni topib beraman, taksi va do'konlar bo'yicha yordam beraman.\n\n"
      "Savolingizni yozing yoki pastdagi tugmalardan tanlang.",
      mine: false,
    ));
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 220), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send(String raw) async {
    final text = raw.trim();
    if (_busy || text.isEmpty) return;
    _input.clear();
    setState(() {
      _busy = true;
      _items.add(_Msg(text, mine: true));
    });
    _history.add({'role': 'user', 'content': text});
    _scrollToEnd();

    try {
      final res = await ref.read(assistantRepositoryProvider).chat(
            text,
            lat: _lat,
            lng: _lng,
            history: _history,
            context: _ctx,
          );
      if (!mounted) return;
      setState(() {
        _items.add(_Msg(res.reply, mine: false));
        if (res.cards.isNotEmpty) _items.add(_Cards(res.cards));
        if (res.actions.isNotEmpty) _items.add(_Actions(res.actions));
      });
      _history.add({'role': 'assistant', 'content': res.reply});
      if (res.category != null) {
        _ctx = {'last_category': res.category, 'offset': res.nextOffset};
      } else {
        _ctx = {'last_category': null, 'offset': 0};
      }
    } catch (_) {
      if (mounted) {
        setState(() => _items.add(_Msg(
            "Ulanishda xatolik. Internetni tekshirib, qayta urinib ko'ring.",
            mine: false)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
      _scrollToEnd();
    }
  }

  Future<void> _attachLocation() async {
    if (_locating) return;
    setState(() => _locating = true);
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        _snack("Joylashuv (GPS) o'chirilgan — yoqing");
        return;
      }
      var perm = await Geolocator.checkPermission();
      if (perm == LocationPermission.denied) {
        perm = await Geolocator.requestPermission();
      }
      if (perm == LocationPermission.denied ||
          perm == LocationPermission.deniedForever) {
        _snack('Joylashuvga ruxsat berilmadi');
        return;
      }
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.best, timeLimit: Duration(seconds: 25)),
      );
      _lat = pos.latitude;
      _lng = pos.longitude;
      if (mounted) {
        setState(() => _items.add(_Msg(
            "📍 Joylashuvingiz ulandi. Endi «eng yaqin ...» deb so'rang.",
            mine: false)));
      }
      _scrollToEnd();
    } catch (_) {
      _snack("Joylashuvni aniqlab bo'lmadi");
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _openWeb(String path) async {
    // Nisbiy web yo'lini to'liq manzilga aylantiramiz (samcity.onrender.com/...).
    final host = AppConfig.apiBase.replaceFirst(RegExp(r'/api/?$'), '');
    final uri = Uri.parse(path.startsWith('http') ? path : '$host$path');
    try {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      _snack('Havolani ochib bo\'lmadi');
    }
  }

  Future<void> _openRoute(String url) async {
    try {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } catch (_) {
      _snack('Xaritani ochib bo\'lmadi');
    }
  }

  void _snack(String m) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(m)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: const Color(0x2634D399),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text('🤖', style: TextStyle(fontSize: 18)),
            ),
            const SizedBox(width: 10),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('SamCity yordamchi',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                Text('Onlayn · yordamga tayyor',
                    style: TextStyle(fontSize: 11.5, color: Color(0xFF34D399))),
              ],
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scroll,
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
              itemCount: _items.length + (_busy ? 1 : 0),
              itemBuilder: (_, i) {
                if (i >= _items.length) return const _Typing();
                final it = _items[i];
                return switch (it) {
                  _Msg m => _Bubble(text: m.text, mine: m.mine),
                  _Cards c => _CardsView(
                      cards: c.cards,
                      onRoute: _openRoute,
                      onCall: (p) => callPhone(context, p),
                    ),
                  _Actions a => _ActionsView(
                      actions: a.actions,
                      onSend: _send,
                      onOpen: _openWeb,
                    ),
                };
              },
            ),
          ),
          _Chips(onTap: _busy ? null : _send),
          _InputBar(
            controller: _input,
            busy: _busy,
            locating: _locating,
            hasLocation: _lat != null,
            onSend: () => _send(_input.text),
            onLocation: _attachLocation,
          ),
        ],
      ),
    );
  }
}

// ─── Xabar pufagi ─────────────────────────────────────────────────────────────
class _Bubble extends StatelessWidget {
  const _Bubble({required this.text, required this.mine});
  final String text;
  final bool mine;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
        constraints:
            BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        decoration: BoxDecoration(
          color: mine ? const Color(0xFF34D399) : const Color(0xFF141B29),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(mine ? 16 : 5),
            bottomRight: Radius.circular(mine ? 5 : 16),
          ),
          border: mine ? null : Border.all(color: const Color(0x14FFFFFF)),
        ),
        child: Text(
          text,
          style: TextStyle(
            fontSize: 14.5,
            height: 1.45,
            color: mine ? const Color(0xFF04130D) : const Color(0xFFEAF0F8),
            fontWeight: mine ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}

// ─── Joy kartalari ────────────────────────────────────────────────────────────
class _CardsView extends StatelessWidget {
  const _CardsView(
      {required this.cards, required this.onRoute, required this.onCall});
  final List<AiCard> cards;
  final void Function(String url) onRoute;
  final void Function(String phone) onCall;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: cards.map((c) => _CardTile(c, onRoute: onRoute, onCall: onCall)).toList(),
      ),
    );
  }
}

class _CardTile extends StatelessWidget {
  const _CardTile(this.c, {required this.onRoute, required this.onCall});
  final AiCard c;
  final void Function(String url) onRoute;
  final void Function(String phone) onCall;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F1521),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: const Color(0x14FFFFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(c.icon, style: const TextStyle(fontSize: 22)),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(c.title,
                        style: const TextStyle(
                            fontSize: 14.5, fontWeight: FontWeight.w800)),
                    if (c.subtitle.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 1),
                        child: Text(c.subtitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                fontSize: 12.5, color: Color(0xFF9AA6BD))),
                      ),
                  ],
                ),
              ),
            ],
          ),
          if (_hasMeta) ...[
            const SizedBox(height: 9),
            Wrap(spacing: 6, runSpacing: 6, children: _metaTags()),
          ],
          if (c.routeUrl != null || c.phone != null) ...[
            const SizedBox(height: 10),
            Row(children: [
              if (c.routeUrl != null)
                Expanded(
                  child: _CardBtn(
                    icon: Icons.navigation_outlined,
                    label: "Yo'nalish",
                    onTap: () => onRoute(c.routeUrl!),
                  ),
                ),
              if (c.routeUrl != null && c.phone != null)
                const SizedBox(width: 8),
              if (c.phone != null)
                Expanded(
                  child: _CardBtn(
                    icon: Icons.phone,
                    label: "Qo'ng'iroq",
                    primary: true,
                    onTap: () => onCall(c.phone!),
                  ),
                ),
            ]),
          ],
        ],
      ),
    );
  }

  bool get _hasMeta =>
      c.distance != null || c.walk != null || c.open != null;

  List<Widget> _metaTags() {
    final tags = <Widget>[];
    if (c.distance != null) {
      tags.add(_Tag('📍 ${c.distance}', const Color(0xFF34D399), const Color(0x2634D399)));
    }
    if (c.walk != null) {
      tags.add(_Tag(c.walk!, const Color(0xFF9AA6BD), const Color(0xFF141B29)));
    }
    if (c.open == true) {
      tags.add(const _Tag('● Ochiq', Color(0xFF34D399), Color(0x2610B981)));
    } else if (c.open == false) {
      tags.add(const _Tag('● Yopiq', Color(0xFFF97066), Color(0x26F97066)));
    }
    return tags;
  }
}

class _Tag extends StatelessWidget {
  const _Tag(this.text, this.fg, this.bg);
  final String text;
  final Color fg, bg;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration:
          BoxDecoration(color: bg, borderRadius: BorderRadius.circular(100)),
      child: Text(text,
          style: TextStyle(
              fontSize: 11.5, fontWeight: FontWeight.w700, color: fg)),
    );
  }
}

class _CardBtn extends StatelessWidget {
  const _CardBtn(
      {required this.icon,
      required this.label,
      required this.onTap,
      this.primary = false});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    final fg = primary ? const Color(0xFF04130D) : const Color(0xFF34D399);
    return Material(
      color: primary ? const Color(0xFF34D399) : const Color(0x1A34D399),
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 9),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 16, color: fg),
              const SizedBox(width: 6),
              Text(label,
                  style: TextStyle(
                      fontSize: 12.5, fontWeight: FontWeight.w700, color: fg)),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Tez amallar (yana / xaritada ...) ────────────────────────────────────────
class _ActionsView extends StatelessWidget {
  const _ActionsView(
      {required this.actions, required this.onSend, required this.onOpen});
  final List<AiAction> actions;
  final void Function(String q) onSend;
  final void Function(String url) onOpen;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 2, bottom: 6),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: actions.map((a) {
          return ActionChip(
            label: Text(a.label),
            backgroundColor: const Color(0x1A34D399),
            side: const BorderSide(color: Color(0x3334D399)),
            labelStyle: const TextStyle(
                fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF34D399)),
            onPressed: () {
              if (a.q != null) {
                onSend(a.q!);
              } else if (a.url != null) {
                onOpen(a.url!);
              }
            },
          );
        }).toList(),
      ),
    );
  }
}

// ─── Boshlang'ich tez tugmalar ────────────────────────────────────────────────
class _Chips extends StatelessWidget {
  const _Chips({required this.onTap});
  final void Function(String q)? onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF0F1521),
        border: Border(top: BorderSide(color: Color(0x14FFFFFF))),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: SizedBox(
        height: 34,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: _AssistantScreenState._chips.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) {
            final (label, q) = _AssistantScreenState._chips[i];
            return ActionChip(
              label: Text(label),
              backgroundColor: const Color(0xFF141B29),
              side: const BorderSide(color: Color(0x14FFFFFF)),
              labelStyle: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFFEAF0F8)),
              onPressed: onTap == null ? null : () => onTap!(q),
            );
          },
        ),
      ),
    );
  }
}

// ─── Kiritish paneli (klaviatura "yuborish" ham jo'natadi) ─────────────────────
class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.busy,
    required this.locating,
    required this.hasLocation,
    required this.onSend,
    required this.onLocation,
  });
  final TextEditingController controller;
  final bool busy;
  final bool locating;
  final bool hasLocation;
  final VoidCallback onSend;
  final VoidCallback onLocation;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFF0F1521),
        border: Border(top: BorderSide(color: Color(0x14FFFFFF))),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
          child: Row(
            children: [
              IconButton(
                onPressed: locating ? null : onLocation,
                tooltip: 'Joylashuvni ulash',
                icon: locating
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : Icon(Icons.my_location,
                        color: hasLocation
                            ? const Color(0xFF34D399)
                            : const Color(0xFF9AA6BD)),
              ),
              Expanded(
                child: TextField(
                  controller: controller,
                  textInputAction: TextInputAction.send,
                  minLines: 1,
                  maxLines: 4,
                  onSubmitted: (_) => onSend(),
                  decoration: const InputDecoration(
                    hintText: 'Savolingizni yozing…',
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: busy ? null : onSend,
                style: FilledButton.styleFrom(
                  minimumSize: const Size(48, 48),
                  padding: EdgeInsets.zero,
                  shape: const CircleBorder(),
                ),
                child: busy
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Color(0xFF04130D)))
                    : const Icon(Icons.send, size: 20),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── "Yozyapti…" indikatori ───────────────────────────────────────────────────
class _Typing extends StatelessWidget {
  const _Typing();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: const Color(0xFF141B29),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0x14FFFFFF)),
        ),
        child: const SizedBox(
          width: 34,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Dot(0), _Dot(150), _Dot(300),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot(this.delayMs);
  final int delayMs;

  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  );

  @override
  void initState() {
    super.initState();
    Future.delayed(Duration(milliseconds: widget.delayMs), () {
      if (mounted) _c.repeat(reverse: true);
    });
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween(begin: 0.3, end: 1.0).animate(_c),
      child: Container(
        width: 7,
        height: 7,
        decoration: const BoxDecoration(
            color: Color(0xFF9AA6BD), shape: BoxShape.circle),
      ),
    );
  }
}

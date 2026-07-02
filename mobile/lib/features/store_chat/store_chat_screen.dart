import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import 'store_chat_models.dart';
import 'store_chat_socket.dart';

/// Do'kon bilan chat oynasi — xabar tarixi + real-time WebSocket.
class StoreChatScreen extends ConsumerStatefulWidget {
  const StoreChatScreen({super.key, required this.threadId, this.title = "Do'kon"});
  final String threadId;
  final String title;

  @override
  ConsumerState<StoreChatScreen> createState() => _StoreChatScreenState();
}

class _StoreChatScreenState extends ConsumerState<StoreChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<StoreChatMessage> _messages = [];
  StoreChatSocket? _socket;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final history =
          await ref.read(storeChatRepositoryProvider).messages(widget.threadId);
      if (!mounted) return;
      setState(() {
        _messages
          ..clear()
          ..addAll(history);
        _loading = false;
      });
      _scrollToEnd();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
    _connectSocket();
  }

  Future<void> _connectSocket() async {
    final socket = StoreChatSocket(ref.read(tokenStorageProvider));
    _socket = socket;
    socket.messages.listen((m) {
      if (!mounted) return;
      // Dublikat bo'lmasligi uchun id bo'yicha tekshiramiz.
      if (_messages.any((x) => x.id == m.id)) return;
      setState(() => _messages.add(m));
      _scrollToEnd();
    });
    await socket.connect(widget.threadId);
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    _input.clear();
    final socket = _socket;
    if (socket != null && socket.isOpen) {
      socket.send(text); // jonli — javob WS orqali qaytadi
    } else {
      // Fallback: REST orqali yuboramiz va ro'yxatga qo'shamiz.
      try {
        final m = await ref.read(storeChatRepositoryProvider).send(widget.threadId, text);
        if (mounted) {
          setState(() => _messages.add(m));
          _scrollToEnd();
        }
      } catch (_) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Xabar yuborilmadi')));
        }
      }
    }
  }

  @override
  void dispose() {
    _socket?.dispose();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final myId = ref.watch(authControllerProvider).user?.id;
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? const Center(child: Text('Hali xabar yo\'q. Birinchi bo\'lib yozing.'))
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.all(12),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final m = _messages[i];
                          final mine = m.senderId == myId;
                          return _Bubble(text: m.text, mine: mine);
                        },
                      ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _send(),
                    decoration: const InputDecoration(
                      hintText: 'Xabar yozing...',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(onPressed: _send, child: const Icon(Icons.send, size: 20)),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

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
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: mine ? Theme.of(context).colorScheme.primary : const Color(0xFF1B2436),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(text,
            style: TextStyle(color: mine ? Colors.white : const Color(0xFFE6ECF5))),
      ),
    );
  }
}

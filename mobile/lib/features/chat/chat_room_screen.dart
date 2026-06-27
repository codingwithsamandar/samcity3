import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/providers.dart';
import 'chat_models.dart';
import 'chat_socket.dart';

/// Bitta chat xonasi — real-time (WebSocket) xabarlar.
/// Tarix REST orqali yuklanadi, yangi xabarlar WebSocket orqali bir zumda keladi.
/// WebSocket ulanmasa — har 4 soniyada yangilanishga (polling) qaytadi.
class ChatRoomScreen extends ConsumerStatefulWidget {
  const ChatRoomScreen({super.key, required this.roomId, required this.title});
  final String roomId;
  final String title;

  @override
  ConsumerState<ChatRoomScreen> createState() => _ChatRoomScreenState();
}

class _ChatRoomScreenState extends ConsumerState<ChatRoomScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final _ids = <String>{};
  final List<ChatMessage> _messages = [];

  ChatSocket? _socket;
  Timer? _pollTimer;
  bool _live = false;
  bool _canWrite = false;
  bool _loading = true;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    await _loadHistory(initial: true);
    await _connectSocket();
  }

  Future<void> _loadHistory({bool initial = false}) async {
    try {
      final h = await ref.read(chatRepositoryProvider).messages(widget.roomId);
      if (!mounted) return;
      final atBottom = !_scroll.hasClients ||
          _scroll.position.pixels >= _scroll.position.maxScrollExtent - 80;
      for (final m in h.messages) {
        if (_ids.add(m.id)) _messages.add(m);
      }
      setState(() {
        _canWrite = h.canWrite;
        _loading = false;
      });
      if (initial || atBottom) _jumpToBottom();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _connectSocket() async {
    final socket = ChatSocket(ref.read(tokenStorageProvider));
    _socket = socket;
    socket.messages.listen((m) {
      if (!mounted) return;
      if (_ids.add(m.id)) {
        setState(() => _messages.add(m));
        _jumpToBottom();
      }
    });
    socket.canWrite.listen((v) {
      if (mounted) setState(() => _canWrite = v);
    });
    // _live faqat server 'status' javobini bergach (haqiqiy ulanish) yoqiladi.
    socket.connected.listen((up) {
      if (!mounted) return;
      if (up && !_live) {
        setState(() => _live = true);
        _pollTimer?.cancel();
      } else if (!up && _live) {
        setState(() => _live = false);
        _startPolling();
      }
    });
    await socket.connect(widget.roomId);
    // Ulanish tasdiqlanguncha polling bilan ishlaymiz (xabar yo'qolmasligi uchun).
    _startPolling();
  }

  void _startPolling() {
    _pollTimer?.cancel();
    _pollTimer =
        Timer.periodic(const Duration(seconds: 4), (_) => _loadHistory());
  }

  void _jumpToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  Future<void> _send() async {
    final text = _input.text.trim();
    if (text.isEmpty) return;
    _input.clear();

    if (_live && _socket != null) {
      // Real-time: yuboramiz, xabar echo orqali qaytadi.
      _socket!.send(text);
      return;
    }
    // Fallback: REST
    setState(() => _sending = true);
    try {
      final msg = await ref.read(chatRepositoryProvider).send(widget.roomId, text);
      if (_ids.add(msg.id)) setState(() => _messages.add(msg));
      _jumpToBottom();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Xabar yuborilmadi')));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _socket?.dispose();
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final myId = ref.watch(authControllerProvider).user?.id ?? '';
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.title),
            Text(
              _live ? 'Onlayn · real-time' : 'Yangilanmoqda...',
              style: TextStyle(
                  fontSize: 11,
                  color: _live ? const Color(0xFF34D399) : const Color(0xFF9AA6BD)),
            ),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? const Center(child: Text('Hali xabarlar yo\'q'))
                    : ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.all(12),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final m = _messages[i];
                          return _Bubble(message: m, mine: m.userId == myId);
                        },
                      ),
          ),
          if (_canWrite)
            _Composer(controller: _input, sending: _sending, onSend: _send)
          else
            Container(
              width: double.infinity,
              padding: EdgeInsets.fromLTRB(
                  16, 12, 16, MediaQuery.of(context).padding.bottom + 12),
              color: const Color(0xFF141B29),
              child: const Text(
                "Yozish uchun mahalla admini tasdig'i kerak.",
                textAlign: TextAlign.center,
                style: TextStyle(color: Color(0xFF9AA6BD)),
              ),
            ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, required this.mine});
  final ChatMessage message;
  final bool mine;

  @override
  Widget build(BuildContext context) {
    final time = message.createdAt != null
        ? DateFormat('HH:mm').format(message.createdAt!.toLocal())
        : '';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.76),
        decoration: BoxDecoration(
          color: mine ? const Color(0xFF0B7D57) : const Color(0xFF141B29),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(14),
            topRight: const Radius.circular(14),
            bottomLeft: Radius.circular(mine ? 14 : 4),
            bottomRight: Radius.circular(mine ? 4 : 14),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!mine)
              Text(
                message.isAdminMessage ? 'Admin' : message.userName,
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: message.isAdminMessage
                        ? const Color(0xFFCAA23A)
                        : const Color(0xFF34D399)),
              ),
            if (message.replyToText != null)
              Container(
                margin: const EdgeInsets.only(top: 2, bottom: 4),
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                  border: const Border(
                      left: BorderSide(color: Color(0xFF34D399), width: 3)),
                ),
                child: Text(message.replyToText!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, color: Color(0xFF9AA6BD))),
              ),
            if (message.text.isNotEmpty) Text(message.text),
            if (message.image != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.network(message.image!,
                      width: 200, fit: BoxFit.cover),
                ),
              ),
            const SizedBox(height: 2),
            Text(time,
                style: const TextStyle(fontSize: 10, color: Color(0xFF9AA6BD))),
          ],
        ),
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.controller,
    required this.sending,
    required this.onSend,
  });
  final TextEditingController controller;
  final bool sending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.fromLTRB(
          12, 8, 12, MediaQuery.of(context).padding.bottom + 8),
      decoration: const BoxDecoration(
        color: Color(0xFF0F1521),
        border: Border(top: BorderSide(color: Color(0x14FFFFFF))),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => onSend(),
              decoration: const InputDecoration(
                hintText: 'Xabar yozing...',
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              ),
            ),
          ),
          const SizedBox(width: 8),
          sending
              ? const Padding(
                  padding: EdgeInsets.all(10),
                  child: SizedBox(
                      height: 22, width: 22,
                      child: CircularProgressIndicator(strokeWidth: 2)),
                )
              : IconButton.filled(
                  onPressed: onSend,
                  icon: const Icon(Icons.send),
                  style: IconButton.styleFrom(
                      backgroundColor: const Color(0xFF34D399),
                      foregroundColor: const Color(0xFF04130D)),
                ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import 'chat_models.dart';

/// Mahalla chat xonalari ro'yxati.
class ChatRoomsScreen extends ConsumerStatefulWidget {
  const ChatRoomsScreen({super.key});

  @override
  ConsumerState<ChatRoomsScreen> createState() => _ChatRoomsScreenState();
}

class _ChatRoomsScreenState extends ConsumerState<ChatRoomsScreen> {
  late Future<List<ChatRoom>> _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(chatRepositoryProvider).rooms();
  }

  void _reload() =>
      setState(() => _future = ref.read(chatRepositoryProvider).rooms());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Chat')),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<List<ChatRoom>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Chatlarni yuklab bo'lmadi")),
              ]);
            }
            final rooms = snap.data ?? [];
            if (rooms.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: Text("Hozircha chat xonalari yo'q")),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(8),
              itemCount: rooms.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) => _RoomTile(room: rooms[i]),
            );
          },
        ),
      ),
    );
  }
}

class _RoomTile extends StatelessWidget {
  const _RoomTile({required this.room});
  final ChatRoom room;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: const Color(0xFF141B29),
        child: Text(room.name.isNotEmpty ? room.name[0] : '#',
            style: const TextStyle(
                color: Color(0xFF34D399), fontWeight: FontWeight.w800)),
      ),
      title: Text(room.name, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(
        room.lastMessageText ?? '${room.memberCount} a\'zo',
        maxLines: 1, overflow: TextOverflow.ellipsis,
      ),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => context.push('/chat/${room.id}', extra: room.name),
    );
  }
}

class PollOption {
  final int id;
  final String text;
  final int votes;
  PollOption({required this.id, required this.text, required this.votes});
  factory PollOption.fromJson(Map<String, dynamic> j) => PollOption(
        id: j['id'] is int ? j['id'] : int.tryParse('${j['id']}') ?? 0,
        text: j['text'] ?? '',
        votes: j['votes'] ?? 0,
      );
}

class Poll {
  final String id;
  final String question;
  final String description;
  final String pollType; // single | multiple
  final bool isOpen;
  final int totalVotes;
  final List<PollOption> options;
  final List<int> myVotes;
  final String creatorName;

  Poll({
    required this.id,
    required this.question,
    required this.description,
    required this.pollType,
    required this.isOpen,
    required this.totalVotes,
    required this.options,
    required this.myVotes,
    required this.creatorName,
  });

  factory Poll.fromJson(Map<String, dynamic> j) => Poll(
        id: j['id'].toString(),
        question: j['question'] ?? '',
        description: j['description'] ?? '',
        pollType: j['poll_type'] ?? 'single',
        isOpen: j['is_open'] ?? true,
        totalVotes: j['total_votes'] ?? 0,
        options: ((j['options'] as List?) ?? [])
            .map((e) => PollOption.fromJson(e))
            .toList(),
        myVotes: ((j['my_votes'] as List?) ?? [])
            .map((e) => e is int ? e : int.tryParse('$e') ?? 0)
            .toList(),
        creatorName: j['creator_name'] ?? '',
      );

  bool get voted => myVotes.isNotEmpty;
}

class HelpRequest {
  final String id;
  final String kind;
  final String kindLabel;
  final String category;
  final String categoryLabel;
  final String title;
  final String description;
  final String location;
  final String phone;
  final String? image;
  final String statusLabel;
  final bool isUrgent;
  final String creatorName;

  HelpRequest({
    required this.id,
    required this.kind,
    required this.kindLabel,
    required this.category,
    required this.categoryLabel,
    required this.title,
    required this.description,
    required this.location,
    required this.phone,
    this.image,
    required this.statusLabel,
    required this.isUrgent,
    required this.creatorName,
  });

  factory HelpRequest.fromJson(Map<String, dynamic> j) => HelpRequest(
        id: j['id'].toString(),
        kind: j['kind'] ?? 'request',
        kindLabel: j['kind_label'] ?? '',
        category: j['category'] ?? '',
        categoryLabel: j['category_label'] ?? '',
        title: j['title'] ?? '',
        description: j['description'] ?? '',
        location: j['location'] ?? '',
        phone: j['phone'] ?? '',
        image: (j['image'] is String && (j['image'] as String).isNotEmpty) ? j['image'] : null,
        statusLabel: j['status_label'] ?? '',
        isUrgent: j['is_urgent'] ?? false,
        creatorName: j['creator_name'] ?? '',
      );
}

class HelpCategory {
  final String key;
  final String label;
  HelpCategory({required this.key, required this.label});
  factory HelpCategory.fromJson(Map<String, dynamic> j) =>
      HelpCategory(key: j['key'] ?? '', label: j['label'] ?? '');
}

import '../delivery/delivery_models.dart' show money;

class JobAd {
  final String id;
  final String title;
  final String company;
  final String jobTypeLabel;
  final int? salaryMin;
  final int? salaryMax;
  final String location;
  final String description;
  final String requirements;
  final String contactPhone;
  final String contactTelegram;

  JobAd({
    required this.id,
    required this.title,
    required this.company,
    required this.jobTypeLabel,
    this.salaryMin,
    this.salaryMax,
    required this.location,
    required this.description,
    required this.requirements,
    required this.contactPhone,
    required this.contactTelegram,
  });

  factory JobAd.fromJson(Map<String, dynamic> j) => JobAd(
        id: j['id'].toString(),
        title: j['title'] ?? '',
        company: j['company'] ?? '',
        jobTypeLabel: j['job_type_label'] ?? '',
        salaryMin: j['salary_min'],
        salaryMax: j['salary_max'],
        location: j['location'] ?? '',
        description: j['description'] ?? '',
        requirements: j['requirements'] ?? '',
        contactPhone: j['contact_phone'] ?? '',
        contactTelegram: j['contact_telegram'] ?? '',
      );

  String get salaryLabel {
    if (salaryMin != null && salaryMax != null) {
      return "${money(salaryMin!)}–${money(salaryMax!)} so'm";
    }
    if (salaryMin != null) return "${money(salaryMin!)} so'm dan";
    return 'Kelishilgan';
  }
}

class ResumeAd {
  final String id;
  final String title;
  final String experienceLabel;
  final int? salaryMin;
  final String location;
  final String skills;
  final String about;
  final String contactPhone;
  final String contactTelegram;

  ResumeAd({
    required this.id,
    required this.title,
    required this.experienceLabel,
    this.salaryMin,
    required this.location,
    required this.skills,
    required this.about,
    required this.contactPhone,
    required this.contactTelegram,
  });

  factory ResumeAd.fromJson(Map<String, dynamic> j) => ResumeAd(
        id: j['id'].toString(),
        title: j['title'] ?? '',
        experienceLabel: j['experience_label'] ?? '',
        salaryMin: j['salary_min'],
        location: j['location'] ?? '',
        skills: j['skills'] ?? '',
        about: j['about'] ?? '',
        contactPhone: j['contact_phone'] ?? '',
        contactTelegram: j['contact_telegram'] ?? '',
      );

  String get salaryLabel =>
      salaryMin != null ? "${money(salaryMin!)} so'm dan" : 'Kelishilgan';
}

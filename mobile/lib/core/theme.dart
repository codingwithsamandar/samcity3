import 'package:flutter/material.dart';

/// SamCity dizayn-tizimi (web saytdagi emerald/teal palitra asosida).
class AppTheme {
  static const Color emerald = Color(0xFF10B981);
  static const Color emeraldDark = Color(0xFF0B7D57);
  static const Color teal = Color(0xFF22D3EE);
  static const Color gold = Color(0xFFCAA23A);

  // Qorong'i (asosiy brend rejimi)
  static const Color bgDark = Color(0xFF070A10);
  static const Color surfaceDark = Color(0xFF0F1521);
  static const Color surface2Dark = Color(0xFF141B29);
  static const Color textDark = Color(0xFFEAF0F8);
  static const Color text2Dark = Color(0xFF9AA6BD);

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: emerald,
      brightness: Brightness.dark,
    ).copyWith(
      primary: const Color(0xFF34D399),
      secondary: teal,
      surface: surfaceDark,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgDark,
      colorScheme: scheme,
      appBarTheme: const AppBarTheme(
        backgroundColor: bgDark,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textDark, fontSize: 20, fontWeight: FontWeight.w800,
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceDark,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: Color(0x14FFFFFF)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface2Dark,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0xFF34D399),
          foregroundColor: const Color(0xFF04130D),
          padding: const EdgeInsets.symmetric(vertical: 15, horizontal: 20),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: const Color(0xFF34D399),
          side: const BorderSide(color: Color(0x4D34D399)),
          padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: const Color(0xFF34D399),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: surface2Dark,
          foregroundColor: textDark,
          elevation: 0,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surfaceDark,
        elevation: 0,
        height: 66,
        indicatorColor: const Color(0x2634D399),
        labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              color: s.contains(WidgetState.selected)
                  ? const Color(0xFF34D399)
                  : text2Dark,
            )),
        iconTheme: WidgetStateProperty.resolveWith((s) => IconThemeData(
              color: s.contains(WidgetState.selected)
                  ? const Color(0xFF34D399)
                  : text2Dark,
            )),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: surface2Dark,
        contentTextStyle: const TextStyle(color: textDark, fontSize: 14),
        actionTextColor: const Color(0xFF34D399),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        insetPadding: const EdgeInsets.all(12),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surface2Dark,
        selectedColor: const Color(0xFF34D399),
        side: BorderSide.none,
        labelStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
        secondaryLabelStyle: const TextStyle(
            fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF04130D)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      ),
      dividerTheme: const DividerThemeData(
          color: Color(0x14FFFFFF), thickness: 1, space: 1),
      listTileTheme: const ListTileThemeData(iconColor: text2Dark),
    );
  }
}

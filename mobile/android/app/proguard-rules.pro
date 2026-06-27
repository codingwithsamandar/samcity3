# ── Flutter / plaginlar uchun R8 keep qoidalari ───────────────────────────
# Flutter engine
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-keep class io.flutter.embedding.** { *; }
-dontwarn io.flutter.embedding.**

# flutter_secure_storage (Tink/Keystore)
-keep class com.it_nomads.fluttersecurestorage.** { *; }

# Annotatsiyalar va native metodlarni saqlash
-keepattributes *Annotation*
-keepclasseswithmembernames class * {
    native <methods>;
}

# Enum valueslarni saqlash (ba'zi plaginlar reflection bilan ishlatadi)
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

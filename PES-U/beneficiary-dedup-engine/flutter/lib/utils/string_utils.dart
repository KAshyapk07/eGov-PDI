/// String utility functions for name preprocessing before matching.
class StringUtils {
  /// Normalize a name for comparison:
  /// - Lowercase
  /// - Remove diacriticals (e.g., e with accent -> e)
  /// - Trim whitespace
  /// - Collapse multiple spaces
  static String normalizeName(String name) {
    // TODO: Implement full normalization with diacritical removal
    return name.toLowerCase().trim().replaceAll(RegExp(r'\s+'), ' ');
  }

  /// Remove common prefixes/suffixes that don't affect identity
  /// (e.g., "Al-", "El-", "M'" in African/Arabic names)
  static String removeAffixes(String name) {
    // TODO: Implement affix removal for African naming conventions
    return name;
  }
}

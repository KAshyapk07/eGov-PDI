/// Soundex phonetic algorithm implementation.
///
/// Converts a name into a 4-character phonetic code where
/// similar-sounding names produce the same code.
/// Example: "Mahamat" and "Muhammad" both produce "M530".
class Soundex {
  /// Compute the Soundex code for a given string.
  /// Returns a 4-character code (letter + 3 digits).
  static String encode(String input) {
    // TODO: Implement Soundex algorithm
    // 1. Keep first letter
    // 2. Replace consonants with digits (B,F,P,V->1; C,G,J,K,Q,S,X,Z->2; D,T->3; L->4; M,N->5; R->6)
    // 3. Remove adjacent duplicates
    // 4. Remove vowels (A,E,I,O,U,H,W,Y)
    // 5. Pad/truncate to 4 characters
    throw UnimplementedError();
  }
}

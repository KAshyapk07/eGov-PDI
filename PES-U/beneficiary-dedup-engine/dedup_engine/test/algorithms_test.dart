import 'package:test/test.dart';
import 'package:dedup_engine/dedup_engine.dart';

/// Tolerance for floating-point comparisons against the Python reference.
const double eps = 0.001;

void main() {
  // ── Jaro-Winkler ────────────────────────────────────────────────────────
  group('jaroWinklerSimilarity', () {
    test('identical strings are 1.0', () {
      expect(jaroWinklerSimilarity('ibrahim', 'ibrahim'), closeTo(1.0, eps));
    });

    test('fatime vs fatima matches Python (0.9333)', () {
      expect(jaroWinklerSimilarity('fatime', 'fatima'), closeTo(0.9333, eps));
    });

    test('mahamat vs mohamed matches Python (0.6679)', () {
      expect(jaroWinklerSimilarity('mahamat', 'mohamed'), closeTo(0.6679, eps));
    });

    test('no common characters is 0.0', () {
      expect(jaroWinklerSimilarity('abc', 'xyz'), closeTo(0.0, eps));
    });

    test('plain Jaro (no prefix boost) matches Python (0.8889)', () {
      expect(jaroSimilarity('fatime', 'fatima'), closeTo(0.8889, eps));
    });

    test('prefix boost makes JW >= Jaro', () {
      final j = jaroSimilarity('fatime', 'fatima');
      final jw = jaroWinklerSimilarity('fatime', 'fatima');
      expect(jw, greaterThanOrEqualTo(j));
    });
  });

  // ── Soundex ─────────────────────────────────────────────────────────────
  group('soundex', () {
    test('Robert and Rupert both encode to R163', () {
      expect(soundex('Robert'), 'R163');
      expect(soundex('Rupert'), 'R163');
    });

    test('Ibrahim encodes to I165', () {
      expect(soundex('Ibrahim'), 'I165');
    });

    test('Tymczak encodes to T522', () {
      expect(soundex('Tymczak'), 'T522');
    });

    test('empty input gives empty string', () {
      expect(soundex(''), '');
    });

    test('soundexMatch is 1.0 for same-sounding names', () {
      expect(soundexMatch('Robert', 'Rupert'), 1.0);
      expect(soundexMatch('Robert', 'Fatima'), 0.0);
    });
  });

  // ── Double Metaphone ────────────────────────────────────────────────────
  group('doubleMetaphone', () {
    test('mahamat and muhammad both encode to MHMT', () {
      expect(doubleMetaphone('mahamat').primary, 'MHMT');
      expect(doubleMetaphone('muhammad').primary, 'MHMT');
    });

    test('khadija encodes to KTJ', () {
      expect(doubleMetaphone('khadija').primary, 'KTJ');
    });

    test('ibrahim encodes to APRH', () {
      expect(doubleMetaphone('ibrahim').primary, 'APRH');
    });

    test('metaphoneMatch catches the transliteration variant', () {
      expect(metaphoneMatch('mahamat', 'muhammad'), 1.0);
    });

    test('metaphoneMatch is 0.0 for unrelated names', () {
      expect(metaphoneMatch('mahamat', 'fatima'), 0.0);
    });

    test('empty input gives empty codes', () {
      expect(doubleMetaphone('').primary, '');
    });
  });

  // ── String normalization ────────────────────────────────────────────────
  group('normalizeName', () {
    test('Oumar -> umar (ou transliteration)', () {
      expect(normalizeName('Oumar'), 'umar');
    });

    test('strips diacritics: Mahamat with accent -> mahamat', () {
      expect(normalizeName('Mah\u00e0mat'), 'mahamat');
    });

    test("removes apostrophes: 'Umar -> umar", () {
      expect(normalizeName("'Umar"), 'umar');
    });

    test('Khalil -> kalil (kh transliteration)', () {
      expect(normalizeName('Khalil'), 'kalil');
    });

    test('Djimadoum -> jimadum (dj and ou)', () {
      expect(normalizeName('Djimadoum'), 'jimadum');
    });

    test('null and empty are safe', () {
      expect(normalizeName(null), '');
      expect(normalizeName(''), '');
    });
  });

  group('tokenSort', () {
    test('sorts tokens so name order does not matter', () {
      expect(tokenSort('saleh mahamat'), 'mahamat saleh');
      expect(tokenSort('mahamat saleh'), 'mahamat saleh');
    });
  });

  // ── GPS ─────────────────────────────────────────────────────────────────
  group('gps', () {
    test('haversine 0.001 degrees latitude is ~111 m', () {
      final km = haversineKm(12.1934, 15.0716, 12.1944, 15.0716);
      expect(km, closeTo(0.1112, 0.001));
    });

    test('same point has proximity 1.0', () {
      expect(proximityScore(12.1, 15.0, 12.1, 15.0), closeTo(1.0, eps));
    });

    test('0.001 degrees apart matches Python (0.7776)', () {
      final p = proximityScore(12.1934, 15.0716, 12.1944, 15.0716);
      expect(p, closeTo(0.7776, eps));
    });

    test('null coordinates give 0.0', () {
      expect(proximityScore(null, 15.0, 12.1, 15.0), 0.0);
      expect(proximityScore(12.1, null, 12.1, 15.0), 0.0);
    });

    test('poor accuracy applies a penalty', () {
      final good = proximityScore(12.1, 15.0, 12.1, 15.0, acc1: 5, acc2: 5);
      final bad = proximityScore(12.1, 15.0, 12.1, 15.0, acc1: 60, acc2: 60);
      expect(bad, lessThan(good));
    });

    test('sameHouseholdScore is stricter than proximityScore', () {
      final prox = proximityScore(12.1934, 15.0716, 12.1944, 15.0716);
      final house = sameHouseholdScore(12.1934, 15.0716, 12.1944, 15.0716);
      expect(house, lessThan(prox));
    });
  });
}

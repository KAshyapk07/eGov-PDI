"""
Synthetic Dataset Generator for HCM Beneficiary Registration Flow (v2 - 50K Scale)
====================================================================================
Generates training data for the Beneficiary Deduplication Engine.

Scale: 50,000 individuals + 5,000 deliberate duplicates = 55,000 total records
       ~12,000 households

Models generated (matching transformer_config.dart):
  1. Household
  2. Individual (with Name, Address, Identifier)
  3. HouseholdMember (links Household <-> Individual)
  4. ProjectBeneficiary (links Individual/Household to Campaign)

Features:
  - 200+ unique African names (Arabic, French, Sara, Kanuri, Fulani, Hausa)
  - 5,000 deliberate duplicate pairs with 12 variation strategies
  - Edge cases: single-char names, hyphens, apostrophes, diacritics,
    name-swaps, nicknames, transliteration, missing fields, gender-ambiguous
  - Real boundary codes from POLIO_CHAD campaign
  - GPS coordinates in N'Djamena, Chad area
  - Batch SQL inserts for fast loading
"""

import uuid
import random
import csv
import os
import sys
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================
TENANT_ID = "mz"
PROJECT_ID = "POLIO_CHAD_2024"
BENEFICIARY_TYPE = "INDIVIDUAL"

NUM_UNIQUE_INDIVIDUALS = 50000
NUM_DUPLICATE_PAIRS = 5000
# Households auto-calculated from individuals (~4 members avg)

BASE_LAT = 12.1348
BASE_LON = 15.0557

SEED = 42
random.seed(SEED)

SQL_BATCH_SIZE = 200  # rows per INSERT statement

# ============================================================
# BOUNDARY DATA (from POLIO_CHAD.xlsx - expanded)
# ============================================================
BOUNDARIES = [
    # 9e ARRONDISSEMENT
    {"code": "POLIO_CHAD_CH_01_10_18_16_CARR__9_POL_42", "name": "CARRE 9 POL 42", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA NGOUMNA"},
    {"code": "POLIO_CHAD_CH_01_10_18_15_CARR__8_POL_52", "name": "CARRE 8 POL 52", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA NGOUMNA"},
    {"code": "POLIO_CHAD_CH_01_10_18_14_CARR__7_POL_48", "name": "CARRE 7 POL 48", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA NGOUMNA"},
    {"code": "POLIO_CHAD_CH_01_10_18_13_CARR__6_POL_47", "name": "CARRE 6 POL 47", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA NGOUMNA"},
    {"code": "POLIO_CHAD_CH_01_10_18_12_CARR__5_POL_50", "name": "CARRE 5 POL 50", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA NGOUMNA"},
    {"code": "POLIO_CHAD_CH_01_10_17_10_CARR__8_POL_51", "name": "CARRE 8 POL 51", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA HADJARAI"},
    {"code": "POLIO_CHAD_CH_01_10_17_09_CARR__6_POL_46", "name": "CARRE 6 POL 46", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA HADJARAI"},
    {"code": "POLIO_CHAD_CH_01_10_16_CS_WALIA_EST", "name": "WALIA EST", "district": "9e ARRONDISSEMENT", "facility": "CS WALIA EST"},
    {"code": "POLIO_CHAD_CH_01_10_15_CS_TOUKRA_III", "name": "TOUKRA III", "district": "9e ARRONDISSEMENT", "facility": "CS TOUKRA III"},
    {"code": "POLIO_CHAD_CH_01_10_14_CS_TOUKRA_II", "name": "TOUKRA II", "district": "9e ARRONDISSEMENT", "facility": "CS TOUKRA II"},
    {"code": "POLIO_CHAD_CH_01_10_13_CS_TOUKRA_I", "name": "TOUKRA I", "district": "9e ARRONDISSEMENT", "facility": "CS TOUKRA I"},
    {"code": "POLIO_CHAD_CH_01_10_12_CS_SAINTE_THERESE", "name": "SAINTE THERESE", "district": "9e ARRONDISSEMENT", "facility": "CS SAINTE THERESE"},
    {"code": "POLIO_CHAD_CH_01_10_10_CS_NGUELI", "name": "NGUELI", "district": "9e ARRONDISSEMENT", "facility": "CS NGUELI"},
    {"code": "POLIO_CHAD_CH_01_10_09_CS_NGOUNBA_MASSA", "name": "NGOUNBA MASSA", "district": "9e ARRONDISSEMENT", "facility": "CS NGOUNBA MASSA"},
    # 1er-8e ARRONDISSEMENT
    {"code": "POLIO_CHAD_CH_01_01_01_CS_AMTOUKOUI", "name": "AMTOUKOUI", "district": "1er ARRONDISSEMENT", "facility": "CS AMTOUKOUI"},
    {"code": "POLIO_CHAD_CH_01_01_02_CS_SABANGALI", "name": "SABANGALI", "district": "1er ARRONDISSEMENT", "facility": "CS SABANGALI"},
    {"code": "POLIO_CHAD_CH_01_01_03_CS_BOLOLO", "name": "BOLOLO", "district": "1er ARRONDISSEMENT", "facility": "CS BOLOLO"},
    {"code": "POLIO_CHAD_CH_01_02_01_CS_PARIS_CONGO", "name": "PARIS CONGO", "district": "2e ARRONDISSEMENT", "facility": "CS PARIS CONGO"},
    {"code": "POLIO_CHAD_CH_01_02_02_CS_MARDJANDAFACK", "name": "MARDJANDAFACK", "district": "2e ARRONDISSEMENT", "facility": "CS MARDJANDAFACK"},
    {"code": "POLIO_CHAD_CH_01_02_03_CS_KABALAYE", "name": "KABALAYE", "district": "2e ARRONDISSEMENT", "facility": "CS KABALAYE"},
    {"code": "POLIO_CHAD_CH_01_03_01_CS_GARDOLE", "name": "GARDOLE", "district": "3e ARRONDISSEMENT", "facility": "CS GARDOLE"},
    {"code": "POLIO_CHAD_CH_01_03_02_CS_AMRIGUEBE", "name": "AMRIGUEBE", "district": "3e ARRONDISSEMENT", "facility": "CS AMRIGUEBE"},
    {"code": "POLIO_CHAD_CH_01_03_03_CS_ARDEP_TIMANE", "name": "ARDEP-TIMANE", "district": "3e ARRONDISSEMENT", "facility": "CS ARDEP-TIMANE"},
    {"code": "POLIO_CHAD_CH_01_04_01_CS_MOURSAL", "name": "MOURSAL", "district": "4e ARRONDISSEMENT", "facility": "CS MOURSAL"},
    {"code": "POLIO_CHAD_CH_01_04_02_CS_REPOS", "name": "REPOS", "district": "4e ARRONDISSEMENT", "facility": "CS REPOS"},
    {"code": "POLIO_CHAD_CH_01_04_03_CS_KLEMAT", "name": "KLEMAT", "district": "4e ARRONDISSEMENT", "facility": "CS KLEMAT"},
    {"code": "POLIO_CHAD_CH_01_05_01_CS_DEMBE", "name": "DEMBE", "district": "5e ARRONDISSEMENT", "facility": "CS DEMBE"},
    {"code": "POLIO_CHAD_CH_01_05_02_CS_RIDINA", "name": "RIDINA", "district": "5e ARRONDISSEMENT", "facility": "CS RIDINA"},
    {"code": "POLIO_CHAD_CH_01_06_01_CS_CHAGOUA", "name": "CHAGOUA", "district": "6e ARRONDISSEMENT", "facility": "CS CHAGOUA"},
    {"code": "POLIO_CHAD_CH_01_06_02_CS_NDJAMENA_CENTRE", "name": "NDJAMENA CENTRE", "district": "6e ARRONDISSEMENT", "facility": "CS NDJAMENA CENTRE"},
    {"code": "POLIO_CHAD_CH_01_06_03_CS_ABENA", "name": "ABENA", "district": "6e ARRONDISSEMENT", "facility": "CS ABENA"},
    {"code": "POLIO_CHAD_CH_01_07_01_CS_NDJARI", "name": "NDJARI", "district": "7e ARRONDISSEMENT", "facility": "CS NDJARI"},
    {"code": "POLIO_CHAD_CH_01_07_02_CS_HABENA", "name": "HABENA", "district": "7e ARRONDISSEMENT", "facility": "CS HABENA"},
    {"code": "POLIO_CHAD_CH_01_07_03_CS_ANGABO", "name": "ANGABO", "district": "7e ARRONDISSEMENT", "facility": "CS ANGABO"},
    {"code": "POLIO_CHAD_CH_01_08_01_CS_DIGUEL", "name": "DIGUEL", "district": "8e ARRONDISSEMENT", "facility": "CS DIGUEL"},
    {"code": "POLIO_CHAD_CH_01_08_02_CS_AMBASSATNA", "name": "AMBASSATNA", "district": "8e ARRONDISSEMENT", "facility": "CS AMBASSATNA"},
    {"code": "POLIO_CHAD_CH_01_08_03_CS_GASSI", "name": "GASSI", "district": "8e ARRONDISSEMENT", "facility": "CS GASSI"},
    # 10e ARRONDISSEMENT
    {"code": "POLIO_CHAD_CH_01_10_11_CS_ORDRE_DE_MALTE", "name": "ORDRE DE MALTE", "district": "10e ARRONDISSEMENT", "facility": "CS ORDRE DE MALTE"},
    {"code": "POLIO_CHAD_CH_01_10_08_CS_NDJAMENA_FARA", "name": "NDJAMENA FARA", "district": "10e ARRONDISSEMENT", "facility": "CS NDJAMENA FARA"},
    {"code": "POLIO_CHAD_CH_01_10_07_CS_KOUNDOUL", "name": "KOUNDOUL", "district": "10e ARRONDISSEMENT", "facility": "CS KOUNDOUL"},
    {"code": "POLIO_CHAD_CH_01_10_06_CS_ATRONE", "name": "ATRONE", "district": "10e ARRONDISSEMENT", "facility": "CS ATRONE"},
    {"code": "POLIO_CHAD_CH_01_10_05_CS_AMBATTA_1", "name": "AMBATTA 1", "district": "10e ARRONDISSEMENT", "facility": "CS AMBATTA 1"},
    {"code": "POLIO_CHAD_CH_01_10_04_CS_AMBATTA_2", "name": "AMBATTA 2", "district": "10e ARRONDISSEMENT", "facility": "CS AMBATTA 2"},
    {"code": "POLIO_CHAD_CH_01_10_03_CS_AL_AFIA", "name": "AL-AFIA", "district": "10e ARRONDISSEMENT", "facility": "CS AL-AFIA"},
    {"code": "POLIO_CHAD_CH_01_10_02_CS_ALBIR", "name": "ALBIR", "district": "10e ARRONDISSEMENT", "facility": "CS ALBIR"},
]

# ============================================================
# EXPANDED AFRICAN NAME POOLS (200+ names)
# ============================================================

# Male given names - Arabic-influenced (Chad, Central Africa)
MALE_ARABIC = [
    "Mahamat", "Ibrahim", "Abubakar", "Issa", "Youssouf", "Moussa",
    "Oumar", "Abdoulaye", "Adoum", "Hassan", "Idriss", "Djibrine",
    "Ahmat", "Saleh", "Haroun", "Brahim", "Hissein", "Adam",
    "Abdelkerim", "Ousmane", "Suleiman", "Ali", "Hamid", "Tahir",
    "Zakaria", "Yusuf", "Daoud", "Musa", "Abdallah", "Khalil",
    "Sadiq", "Noureddine", "Bashir", "Gamar", "Ramadan", "Abdelaziz",
    "Mahamoud", "Abdelrahim", "Abderaman", "Djibril", "Ismail",
    "Abakar", "Mahamadou", "Souleymane", "Abdramane", "Habib",
    "Nasser", "Mahdi", "Jamal", "Karim", "Rachid", "Moustapha",
    "Aboubakar", "Abdel", "Yacoub", "Younous", "Abba", "Djimet",
    "Mahamat-Saleh", "Ali-Brahim", "Moussa-Idriss", "Hassan-Djibrine",
    "Ahmat-Oumar", "Abdel-Aziz", "Nour-Eddine", "Abd-El-Karim",
]

# Male given names - French-influenced
MALE_FRENCH = [
    "Jean-Pierre", "Francois", "Michel", "Patrice", "Alain", "Claude",
    "Philippe", "Gervais", "Theophile", "Noel", "Emmanuel", "Pascal",
    "Christophe", "Bertrand", "Didier", "Prosper", "Romain", "Sylvain",
    "Andre", "Jacques", "Paul", "Pierre", "Lucien", "Joseph",
    "Celestin", "Desire", "Gilbert", "Mathieu", "Etienne", "Victor",
    "Bernard", "Gerard", "Olivier", "Nicolas", "Martin", "Daniel",
    "Jean-Baptiste", "Jean-Claude", "Jean-Marie", "Jean-Paul",
]

# Male given names - Local Sara / Kanuri / Ngambay
MALE_LOCAL = [
    "Nadjitangar", "Djimadoum", "Ndoubabe", "Mbainaissem", "Beassoum",
    "Togou", "Neloumta", "Kemba", "Nodjiram", "Allaguernon",
    "Ndoumbe", "Koudjinan", "Mbaigane", "Djibat", "Ndouba",
    "Koumadji", "Tamadji", "Koudoussou", "Mayam", "Narbe",
    "Ngakoutou", "Dobingar", "Nadingar", "Ngarbaye", "Maldoum",
    "Laoukein", "Nadjingar", "Bemodjim", "Mbairamadji", "Ndjerassem",
    "Miankeol", "Ngaradoum", "Yorongar", "Kebzabo", "Gali",
    "Djimasngar", "Mbaiassem", "Ngarndje", "Koulbou", "Madji",
    "Ngartoloum", "Djidda", "Ngarssou", "Kosnaye", "Baoua",
]

# Male given names - Hausa / Fulani (common in Chad border regions)
MALE_HAUSA_FULANI = [
    "Bukar", "Modu", "Bello", "Sanda", "Usman", "Aliyu",
    "Garba", "Tanko", "Danladi", "Gambo", "Shehu", "Hamza",
    "Abdou", "Malloum", "Ngolo", "Adamu", "Bala", "Maina",
    "Goni", "Kiari", "Zannah", "Kyari", "Bulama", "Grema",
]

# Female given names - Arabic-influenced
FEMALE_ARABIC = [
    "Fatima", "Amina", "Halima", "Khadija", "Mariam", "Hawa",
    "Zara", "Aicha", "Falmata", "Nana", "Bintou", "Salamatou",
    "Hindou", "Fatime", "Djamila", "Nafissa", "Ramatou", "Habiba",
    "Zenaba", "Kaltouma", "Achta", "Hadja", "Maimouna", "Djibia",
    "Souraya", "Noura", "Samira", "Houda", "Balkissa", "Haoua",
    "Fatimatou", "Oumou", "Zahra", "Rokia", "Mafouda", "Zouleikha",
    "Aishatou", "Hassanatou", "Ramla", "Alhadja", "Mabrouka",
    "Oulaye", "Yasmina", "Kalthoum", "Hadjara", "Amira",
    "Fatchima", "Adama", "Mounira", "Sakina", "Wahida", "Leila",
]

# Female given names - Local / French
FEMALE_LOCAL = [
    "Ngarmbatina", "Koubra", "Ndoadoum", "Mbaysabe", "Ngarkidana",
    "Christine", "Therese", "Marie", "Jeanne", "Brigitte",
    "Odette", "Bernadette", "Colette", "Solange", "Germaine",
    "Esperance", "Grace", "Judith", "Rachel", "Ruth",
    "Esther", "Suzanne", "Veronique", "Madeleine", "Catherine",
    "Agnes", "Albertine", "Beatrice", "Dorcas", "Pauline",
    "Marie-Therese", "Marie-Claire", "Anne-Marie", "Marie-Jeanne",
    "Ndolenodji", "Nadjiro", "Ngoniri", "Khadidja", "Djeneba",
    "Koumba", "Asseta", "Oumoul", "Kadidja", "Gogou",
]

# Family names - EXPANDED (100+)
FAMILY_NAMES = [
    "Mahamat", "Deby", "Idriss", "Brahim", "Oumar", "Hassan",
    "Djibrine", "Adam", "Ahmat", "Adoum", "Saleh", "Haroun",
    "Moussa", "Abubakar", "Abdoulaye", "Ousmane", "Suleiman",
    "Togou", "Ndoumbe", "Mbaigane", "Nadjitangar", "Koumadji",
    "Mbainaissem", "Kemba", "Beassoum", "Allaguernon", "Tamadji",
    "Djimadoum", "Ngarmbatina", "Narbe", "Mayam", "Koudoussou",
    "Laoukein", "Ngakoutou", "Dobingar", "Masra", "Pahimi",
    "Moustapha", "Abdramane", "Souleymane", "Abakar", "Bichara",
    "Goukouni", "Kamougue", "Maldoum", "Nadingar", "Ngarbaye",
    # Additional family names
    "Itno", "Habre", "Tombalbaye", "Malloum", "Oueddei",
    "Ngarlejy", "Yorongar", "Kebzabo", "Kasire", "Padacke",
    "Djidda", "Gata", "Ngothodoum", "Kodjo", "Nahor",
    "Mbaitoubam", "Ngarssou", "Djimasngar", "Ngartoloum", "Kosnaye",
    "Boulala", "Hadjerai", "Zaghawa", "Toubou", "Daza",
    "Kanembu", "Kotoko", "Baguirmi", "Barma", "Bilala",
    "Maba", "Massalit", "Tama", "Gimr", "Mbaye",
    "Bongo", "Ngambaye", "Moundang", "Toupouri", "Massa",
    "Moussei", "Marba", "Kim", "Kwang", "Gabri",
    "Somrai", "Nancere", "Lele", "Mesme", "Kenga",
]

# Father/Guardian names (same pool as male given names, flattened)
FATHER_NAMES = MALE_ARABIC[:30] + MALE_FRENCH[:15] + MALE_LOCAL[:15] + MALE_HAUSA_FULANI[:10]

# ============================================================
# PHONETIC VARIATION RULES (Expanded - 80+ entries)
# ============================================================
PHONETIC_VARIATIONS = {
    # --- Arabic male names ---
    "Mahamat": ["Mohamat", "Mohammat", "Mahamad", "Muhammad", "Mohamed", "Mohammed", "Mohamet", "Mahamoud", "Mahamadou", "Mohd"],
    "Ibrahim": ["Ibrahiim", "Ibraheem", "Brahim", "Ibraim", "Ebrahim", "Ibrahima", "Ibrahimu"],
    "Abubakar": ["Aboubakar", "Abu Bakar", "Aboubaker", "Abubakr", "Abubacare", "Aboubakari", "Abu-Bakar"],
    "Moussa": ["Musa", "Mousa", "Mussa", "Moussa-Ali", "Mouça"],
    "Youssouf": ["Yusuf", "Yusuph", "Yousuf", "Youssuf", "Yussuf", "Yousouf", "Yussufu"],
    "Oumar": ["Omar", "Umar", "Oumare", "Oumaru", "Oumarou", "Omaru"],
    "Abdoulaye": ["Abdulaye", "Abdullahi", "Abdulahi", "Abdoulahi", "Abdulai", "Abdoulay"],
    "Issa": ["Isa", "Essa", "Isah", "Issah", "Issaka", "Issa-Adam"],
    "Idriss": ["Idris", "Idrissa", "Idrees", "Edris", "Idrissu", "Idrissou"],
    "Djibrine": ["Djibriine", "Jibrin", "Jibreel", "Djibril", "Jibrine", "Djibreel", "Gibril"],
    "Hassan": ["Hassane", "Hasan", "Hassaan", "Assane", "Hassani", "Assan"],
    "Suleiman": ["Souleymane", "Suleyman", "Sulaiman", "Soulaymane", "Sulaimanu", "Souleman"],
    "Ali": ["Aly", "Aliu", "Aliy", "Alii"],
    "Adam": ["Adamu", "Adama", "Adame", "Adamo"],
    "Ousmane": ["Usman", "Othman", "Osmane", "Ousman", "Osmanu", "Uthman"],
    "Saleh": ["Salih", "Saaleh", "Salh", "Salehi", "Salehe"],
    "Hissein": ["Hussein", "Hussain", "Hissene", "Hisseine", "Husseini", "Husein"],
    "Tahir": ["Taher", "Taheer", "Tahiir", "Taahir"],
    "Khalil": ["Halil", "Kalil", "Khaleel", "Haleel", "Khalilu"],
    "Abdelkerim": ["Abdul-Karim", "Abdel-Karim", "Abdelkarim", "Abdulkarim", "Abd-El-Karim"],
    "Bashir": ["Bachir", "Basheer", "Beshir", "Bacheer"],
    "Hamid": ["Hamed", "Hameed", "Hamidou", "Ahmid"],
    "Zakaria": ["Zakariya", "Zacharia", "Zakariyya", "Zakariaou"],
    "Ismail": ["Ismael", "Ismaila", "Ismaeel", "Esmail"],
    "Moustapha": ["Mustafa", "Moustafa", "Mustapha", "Mostafa"],
    "Abdramane": ["Abderamane", "Abdurahman", "Abderaman", "Abdoul-Rahmane", "Abdul-Rahman"],
    "Habib": ["Habibu", "Habibou", "Habeeb"],
    "Djibril": ["Jibril", "Gabriel", "Jibreel", "Djibrine"],
    "Daoud": ["Dawud", "Dauda", "Daouda", "Dawoud"],
    "Mahamoud": ["Mahmoud", "Mahmud", "Mamadou", "Mahamudu"],
    "Nasser": ["Nasir", "Nassir", "Nassur", "Nacer"],
    # --- Arabic female names ---
    "Fatima": ["Fatouma", "Fatimah", "Fatime", "Fatimatou", "Fatma", "Fatchima", "Fati"],
    "Amina": ["Aminah", "Aminatou", "Aamina", "Amna", "Aminata", "Ami"],
    "Halima": ["Haliima", "Halimah", "Alima", "Halime", "Halimatou", "Alimatou"],
    "Khadija": ["Khadidja", "Kadija", "Khadijah", "Kadidja", "Kadidiatou", "Khadidjatou"],
    "Mariam": ["Maryam", "Mariama", "Meriam", "Myriam", "Mariyama", "Mariame"],
    "Hawa": ["Hauwa", "Haoua", "Hawwa", "Awa", "Hawwa-Djibrine", "Eva"],
    "Zara": ["Zahra", "Zahara", "Zaara", "Zarra", "Zahrah"],
    "Aicha": ["Aisha", "Aysha", "Aishatou", "Aicha", "Aichata", "Aissatou"],
    "Falmata": ["Falmatta", "Falmatah", "Palmata", "Falmmatou"],
    "Maimouna": ["Maimuna", "Maimounah", "Maymuna", "Mamounah", "Maimou"],
    "Salamatou": ["Salamatu", "Salama", "Salamata", "Selam"],
    "Hindou": ["Hindu", "Hinda", "Indou", "Hindoun"],
    "Zenaba": ["Zeinab", "Zainab", "Zineb", "Zeynab", "Zaynab"],
    "Kaltouma": ["Kalthoum", "Kulthum", "Kaltoum", "Koulthoum"],
    "Balkissa": ["Bilkissou", "Bilkis", "Balkis", "Bilkissu"],
    "Haoua": ["Hawa", "Hauwa", "Hawwa", "Awa"],
    "Sakina": ["Sakinah", "Sakine", "Sakeena"],
    "Noura": ["Nura", "Nourah", "Nuraa"],
    "Djamila": ["Jamila", "Djamilla", "Jameela", "Djamilah"],
    # --- French names with accents ---
    "Francois": ["Francoi", "Fransois", "Francoise"],
    "Therese": ["Teresa", "Tereza", "Thereze"],
    "Noel": ["Noelle", "Nowel", "Nohel"],
    "Celestin": ["Celestine", "Celestein", "Selastin"],
    # --- Family name variations ---
    "Deby": ["Deby", "Debi", "Debiy", "D'eby"],
    "Brahim": ["Ibrahima", "Braahim", "Braheem", "Brahim-Mahamat"],
    "Souleymane": ["Suleiman", "Soulaymane", "Suleyman", "Sulemanu"],
    "Abakar": ["Aboubakar", "Abubakar", "Abacare", "Abacare-Mahamat"],
    "Bichara": ["Bishara", "Bechara", "Bishera", "Bichera"],
    "Goukouni": ["Goukounni", "Gukouni", "Goukoune", "Gokouni"],
    "Kamougue": ["Kamogue", "Kamouge", "Kamougué"],
    "Itno": ["Itnoh", "Ittno", "Etno"],
    "Habre": ["Habre", "Habray", "Habrey"],
    "Tombalbaye": ["Tombalbye", "Tombalbaiye", "Tombalbay"],
    # --- Hausa/Kanuri names ---
    "Bukar": ["Boukar", "Bukkar", "Bukarr"],
    "Shehu": ["Shehou", "Sheihu", "Cheihu"],
    "Garba": ["Garbba", "Garbah", "Garba-Oumar"],
    "Modu": ["Modou", "Moodou", "Moddu"],
    "Kyari": ["Kiari", "Kiyari", "Kyaari"],
    "Bulama": ["Boulama", "Bulamma", "Boulamma"],
}

# ============================================================
# EDGE CASE NAME POOLS
# ============================================================

# Single-character / very short names (real in some African contexts)
EDGE_SHORT_NAMES = ["Al", "Ba", "Ka", "Ma", "Na", "Ya", "Da", "Sa", "Ha", "Bi"]

# Very long compound names
EDGE_LONG_NAMES = [
    "Mahamat-Saleh-Ibrahim", "Abdoulaye-Souleymane-Oumar",
    "Jean-Baptiste-Emmanuel", "Marie-Therese-Christine",
    "Abdel-Aziz-Moustapha-Ali", "Fatima-Zahra-Khadija",
    "Ngarmbatina-Ndoumbe-Djimadoum", "Mbainaissem-Togou-Kemba",
]

# Names with apostrophes (common in French-African context)
EDGE_APOSTROPHE_NAMES = [
    "N'Djamena", "N'Golo", "N'Guessan", "D'Almeida", "M'Baye",
    "N'Diaye", "M'Bow", "O'Brien", "D'Souza", "L'Imam",
]

# Names with diacritics
EDGE_DIACRITICAL_NAMES = [
    "Theophile", "Francois", "Noel", "Andre", "Rene",
    "Desire", "Moise", "Jerome", "Genevieve", "Helene",
]
EDGE_DIACRITICAL_VARIANTS = {
    "Theophile": "Théophile",
    "Francois": "François",
    "Noel": "Noël",
    "Andre": "André",
    "Rene": "René",
    "Desire": "Désiré",
    "Moise": "Moïse",
    "Jerome": "Jérôme",
    "Genevieve": "Geneviève",
    "Helene": "Hélène",
}

# Nicknames vs formal names
NICKNAME_MAP = {
    "Mahamat": ["Mat", "Maha", "Hammat"],
    "Ibrahim": ["Ibra", "Brahim", "Ibou"],
    "Abdoulaye": ["Abdou", "Laye", "Abdul"],
    "Moussa": ["Mouss", "Mou"],
    "Fatima": ["Fati", "Tima", "Fatou"],
    "Amina": ["Ami", "Mina", "Minata"],
    "Khadija": ["Kadi", "Dija", "Khadou"],
    "Halima": ["Hali", "Lima", "Alima"],
    "Mariam": ["Mari", "Mimi", "Mariou"],
    "Emmanuel": ["Manu", "Emma", "Emmou"],
    "Christophe": ["Chris", "Toph", "Cristo"],
    "Jean-Pierre": ["JP", "Jean", "Pierre"],
    "Souleymane": ["Soulou", "Soule", "Mane"],
    "Maimouna": ["Maimou", "Mouna", "Mai"],
}

# Gender-ambiguous names (used for both genders in Chad)
GENDER_AMBIGUOUS_NAMES = [
    "Adama", "Djimet", "Ndoumbe", "Koubra", "Bello",
    "Claude", "Dominique", "Camille",
]

# ============================================================
# HELPERS
# ============================================================

def gen_uuid():
    return str(uuid.uuid4())

def gen_timestamp():
    start = datetime(2024, 3, 1)
    end = datetime(2024, 6, 30)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days),
                              seconds=random.randint(0, 86400))).strftime("%Y-%m-%d %H:%M:%S")

def gen_dob(min_months=0, max_months=60):
    today = datetime(2024, 5, 1)
    return (today - timedelta(days=random.randint(min_months, max_months) * 30)).strftime("%Y-%m-%d")

def gen_adult_dob():
    today = datetime(2024, 5, 1)
    return (today - timedelta(days=random.randint(18, 65) * 365 + random.randint(0, 365))).strftime("%Y-%m-%d")

def gen_phone():
    return f"+235{random.choice(['66','68','90','91','95','99'])}{random.randint(100000,999999)}"

def gen_gps(radius_km=8):
    lat = round(BASE_LAT + random.uniform(-radius_km, radius_km) * 0.009, 6)
    lon = round(BASE_LON + random.uniform(-radius_km, radius_km) * 0.009, 6)
    return lat, lon, round(random.uniform(3.0, 25.0), 1)

def gps_variant(lat, lon, acc):
    return (round(lat + random.uniform(-0.0005, 0.0005), 6),
            round(lon + random.uniform(-0.0005, 0.0005), 6),
            round(max(3, acc + random.uniform(-5, 10)), 1))

def pick_gender():
    return random.choice(["MALE", "FEMALE"])

def pick_male_name():
    pool = random.choices([MALE_ARABIC, MALE_FRENCH, MALE_LOCAL, MALE_HAUSA_FULANI],
                          weights=[50, 15, 25, 10])[0]
    return random.choice(pool)

def pick_female_name():
    pool = random.choices([FEMALE_ARABIC, FEMALE_LOCAL], weights=[60, 40])[0]
    return random.choice(pool)

def pick_given_name(gender):
    return pick_male_name() if gender == "MALE" else pick_female_name()

def pick_family_name():
    return random.choice(FAMILY_NAMES)

def pick_father_name():
    return random.choice(FATHER_NAMES)

def pick_boundary():
    return random.choice(BOUNDARIES)

def sql_val(val):
    if val is None:
        return "NULL"
    s = str(val).replace("'", "''")
    return f"'{s}'"

def sql_bool(val):
    return "TRUE" if val else "FALSE"

def progress(current, total, label="Progress"):
    pct = current * 100 // total
    bar = "#" * (pct // 2) + "-" * (50 - pct // 2)
    sys.stdout.write(f"\r  {label}: [{bar}] {pct}% ({current}/{total})")
    sys.stdout.flush()
    if current == total:
        print()

# ============================================================
# DATA STORE
# ============================================================

class DataStore:
    def __init__(self):
        self.households = []
        self.household_addresses = []
        self.individuals = []
        self.individual_names = []
        self.individual_addresses = []
        self.individual_identifiers = []
        self.household_members = []
        self.project_beneficiaries = []

    def add_household(self, boundary, member_count, lat, lon, acc,
                      children_count=0, pregnant_count=0):
        hh_ref = gen_uuid()
        ts = gen_timestamp()
        self.households.append({
            "ref": hh_ref, "memberCount": member_count,
            "lat": lat, "lon": lon,
            "tenantId": TENANT_ID, "householdType": "FAMILY",
            "childrenCount": children_count, "pregnantCount": pregnant_count,
            "ts": ts,
        })
        self.household_addresses.append({
            "ref": gen_uuid(), "hhRef": hh_ref,
            "doorNo": str(random.randint(1, 999)),
            "lat": lat, "lon": lon, "acc": acc,
            "addr1": f"Near {boundary['facility']}",
            "addr2": boundary["district"],
            "locCode": boundary["code"], "locName": boundary["name"],
            "tenantId": TENANT_ID, "ts": ts,
        })
        return hh_ref

    def add_individual(self, given, family, gender, dob, father, husband,
                       boundary, lat, lon, acc, phone=None, is_child=True):
        ind_ref = gen_uuid()
        ts = gen_timestamp()
        idx = len(self.individuals)

        self.individuals.append({
            "ref": ind_ref, "dob": dob, "phone": phone,
            "father": father, "husband": husband,
            "gender": gender, "boundaryCode": boundary["code"],
            "tenantId": TENANT_ID, "ts": ts,
        })
        self.individual_names.append({
            "ref": gen_uuid(), "indRef": ind_ref,
            "given": given, "family": family,
            "tenantId": TENANT_ID, "ts": ts,
        })
        self.individual_addresses.append({
            "ref": gen_uuid(), "indRef": ind_ref,
            "doorNo": str(random.randint(1, 999)),
            "lat": lat, "lon": lon, "acc": acc,
            "addr1": f"Near {boundary['facility']}",
            "addr2": boundary["district"],
            "locCode": boundary["code"], "locName": boundary["name"],
            "tenantId": TENANT_ID, "ts": ts,
        })
        self.individual_identifiers.append({
            "ref": gen_uuid(), "indRef": ind_ref,
            "idType": "DEFAULT" if is_child else "NATIONAL_ID",
            "idValue": gen_uuid(),
            "boundaryCode": boundary["code"],
            "tenantId": TENANT_ID, "ts": ts,
        })

        return ind_ref, idx

    def add_hh_member(self, hh_ref, ind_ref, is_head=False):
        ts = gen_timestamp()
        self.household_members.append({
            "ref": gen_uuid(), "hhRef": hh_ref, "indRef": ind_ref,
            "isHead": is_head, "tenantId": TENANT_ID, "ts": ts,
        })

    def add_project_beneficiary(self, ind_ref):
        ts = gen_timestamp()
        self.project_beneficiaries.append({
            "ref": gen_uuid(), "projectId": PROJECT_ID,
            "tenantId": TENANT_ID, "benefRef": ind_ref,
            "regDate": ts, "ts": ts,
        })


# ============================================================
# DUPLICATE VARIATION STRATEGIES (12 types)
# ============================================================

def _apply_generic_phonetic(name):
    rules = [
        ("ou", "u"), ("u", "ou"), ("ei", "ey"), ("dj", "j"), ("j", "dj"),
        ("ph", "f"), ("th", "t"), ("kh", "k"), ("ss", "s"), ("s", "ss"),
        ("mm", "m"), ("m", "mm"), ("ee", "i"), ("i", "ee"), ("aa", "a"),
        ("a", "ah"), ("oo", "u"), ("ch", "sh"), ("sh", "ch"), ("dj", "g"),
    ]
    rule = random.choice(rules)
    low = name.lower()
    if rule[0] in low:
        idx = low.find(rule[0])
        return name[:idx] + rule[1] + name[idx + len(rule[0]):]
    return name + random.choice(["a", "e", "ou", "i", ""])


def make_variant(orig_given, orig_family, orig_gender, orig_dob, orig_father,
                 orig_lat, orig_lon, orig_acc, orig_boundary):
    """Create a duplicate variant. Returns (new_given, new_family, new_dob,
       new_father, new_lat, new_lon, new_acc, new_boundary, variation_type)"""

    strategies = [
        "phonetic_given",       # Known phonetic map on given name
        "phonetic_family",      # Known phonetic map on family name
        "phonetic_both",        # Both names varied
        "typo_swap",            # Swap adjacent letters
        "typo_drop",            # Drop a letter
        "typo_double",          # Double a letter
        "truncation",           # Truncate name
        "prefix_variation",     # Add/remove African prefix
        "nickname",             # Use nickname instead of formal name
        "name_swap",            # Swap given and family name
        "diacritical",          # With/without accent marks
        "multi_field_drift",    # Everything drifts slightly (hardest case)
    ]

    strategy = random.choice(strategies)
    new_given = orig_given
    new_family = orig_family
    new_dob = orig_dob
    new_father = orig_father
    new_lat, new_lon, new_acc = orig_lat, orig_lon, orig_acc
    new_boundary = orig_boundary

    # --- Strategy implementations ---

    if strategy == "phonetic_given":
        if orig_given in PHONETIC_VARIATIONS:
            new_given = random.choice(PHONETIC_VARIATIONS[orig_given])
        else:
            new_given = _apply_generic_phonetic(orig_given)

    elif strategy == "phonetic_family":
        if orig_family in PHONETIC_VARIATIONS:
            new_family = random.choice(PHONETIC_VARIATIONS[orig_family])
        else:
            new_family = _apply_generic_phonetic(orig_family)

    elif strategy == "phonetic_both":
        new_given = (random.choice(PHONETIC_VARIATIONS[orig_given])
                     if orig_given in PHONETIC_VARIATIONS
                     else _apply_generic_phonetic(orig_given))
        new_family = (random.choice(PHONETIC_VARIATIONS[orig_family])
                      if orig_family in PHONETIC_VARIATIONS
                      else _apply_generic_phonetic(orig_family))

    elif strategy == "typo_swap" and len(orig_given) > 3:
        i = random.randint(1, len(orig_given) - 2)
        c = list(orig_given)
        c[i], c[i+1] = c[i+1], c[i]
        new_given = "".join(c)

    elif strategy == "typo_drop" and len(orig_given) > 3:
        i = random.randint(1, len(orig_given) - 2)
        new_given = orig_given[:i] + orig_given[i+1:]

    elif strategy == "typo_double" and len(orig_given) > 2:
        i = random.randint(0, len(orig_given) - 1)
        new_given = orig_given[:i] + orig_given[i] + orig_given[i:]

    elif strategy == "truncation" and len(orig_given) > 3:
        cut = random.randint(3, len(orig_given) - 1)
        new_given = orig_given[:cut]

    elif strategy == "prefix_variation":
        prefixes = ["El ", "Al-", "Abdel", "Abu ", "El-", "Ould "]
        stripped = False
        for p in prefixes:
            if orig_given.startswith(p):
                new_given = orig_given[len(p):]
                stripped = True
                break
        if not stripped:
            new_given = random.choice(["El ", "Al-", "Abu "]) + orig_given

    elif strategy == "nickname":
        if orig_given in NICKNAME_MAP:
            new_given = random.choice(NICKNAME_MAP[orig_given])
        else:
            # Generic: take first 3-4 chars
            end = max(4, min(4, len(orig_given)))
            new_given = orig_given[:random.randint(3, end)]

    elif strategy == "name_swap":
        new_given = orig_family
        new_family = orig_given

    elif strategy == "diacritical":
        if orig_given in EDGE_DIACRITICAL_VARIANTS:
            new_given = EDGE_DIACRITICAL_VARIANTS[orig_given]
        elif any(c in orig_given for c in "eaiou"):
            # Add random accent
            accent_map = {"e": "é", "a": "â", "i": "ï", "o": "ô", "u": "ù"}
            for char, accented in accent_map.items():
                if char in orig_given:
                    new_given = orig_given.replace(char, accented, 1)
                    break

    elif strategy == "multi_field_drift":
        # The hardest case: everything changes slightly
        if orig_given in PHONETIC_VARIATIONS:
            new_given = random.choice(PHONETIC_VARIATIONS[orig_given])
        else:
            new_given = _apply_generic_phonetic(orig_given)
        if orig_family in PHONETIC_VARIATIONS:
            new_family = random.choice(PHONETIC_VARIATIONS[orig_family])
        # DOB off by days/months
        d = datetime.strptime(orig_dob, "%Y-%m-%d")
        new_dob = (d + timedelta(days=random.choice([0, 30, -30, 60, -60, 365]))).strftime("%Y-%m-%d")
        # GPS drift
        new_lat, new_lon, new_acc = gps_variant(orig_lat, orig_lon, orig_acc)
        # Maybe different boundary
        if random.random() < 0.3:
            new_boundary = pick_boundary()
        # Father name drift
        if orig_father in PHONETIC_VARIATIONS:
            new_father = random.choice(PHONETIC_VARIATIONS[orig_father])

    else:
        # Fallback: generic phonetic on given name
        strategy = "phonetic_given"
        new_given = _apply_generic_phonetic(orig_given)

    # Additional random drifts (applied to some strategies)
    if strategy not in ("multi_field_drift", "name_swap"):
        if random.random() < 0.25:
            new_dob = (datetime.strptime(orig_dob, "%Y-%m-%d") +
                       timedelta(days=random.choice([0, 30, -30]))).strftime("%Y-%m-%d")
        if random.random() < 0.4:
            new_lat, new_lon, new_acc = gps_variant(orig_lat, orig_lon, orig_acc)
        if random.random() < 0.15:
            new_boundary = pick_boundary()

    return (new_given, new_family, new_dob, new_father,
            new_lat, new_lon, new_acc, new_boundary, strategy)


# ============================================================
# MAIN GENERATION
# ============================================================

def generate():
    store = DataStore()
    originals = []  # (idx, given, family, gender, dob, father, boundary, lat, lon, acc)

    print(f"Generating {NUM_UNIQUE_INDIVIDUALS} unique individuals...")
    created = 0
    hh_refs = []

    while created < NUM_UNIQUE_INDIVIDUALS:
        boundary = pick_boundary()
        lat, lon, acc = gen_gps()
        member_count = random.choices([1, 2, 3, 4, 5, 6, 7, 8],
                                       weights=[5, 10, 20, 25, 20, 10, 5, 5])[0]
        remaining = NUM_UNIQUE_INDIVIDUALS - created
        member_count = min(member_count, remaining)

        children = max(0, member_count - random.randint(1, 2))
        pregnant = 1 if random.random() < 0.15 and member_count > 1 else 0

        hh_ref = store.add_household(boundary, member_count, lat, lon, acc,
                                      children, pregnant)
        hh_refs.append(hh_ref)

        # Head of household
        head_gender = random.choice(["MALE", "FEMALE"])

        # Occasionally inject edge case names for the head
        edge_roll = random.random()
        if edge_roll < 0.01:
            head_given = random.choice(EDGE_SHORT_NAMES)
        elif edge_roll < 0.02:
            head_given = random.choice(EDGE_LONG_NAMES)
        elif edge_roll < 0.03:
            head_given = random.choice(EDGE_APOSTROPHE_NAMES)
        elif edge_roll < 0.04:
            head_given = random.choice(GENDER_AMBIGUOUS_NAMES)
        else:
            head_given = pick_given_name(head_gender)

        head_family = pick_family_name()
        head_dob = gen_adult_dob()
        head_father = pick_father_name()
        head_husband = pick_father_name() if head_gender == "FEMALE" else None

        head_ref, head_idx = store.add_individual(
            head_given, head_family, head_gender, head_dob,
            head_father, head_husband, boundary, lat, lon, acc,
            phone=gen_phone(), is_child=False
        )
        store.add_hh_member(hh_ref, head_ref, is_head=True)
        store.add_project_beneficiary(head_ref)
        originals.append((head_idx, head_given, head_family, head_gender,
                          head_dob, head_father, boundary, lat, lon, acc))
        created += 1

        # Children / other members
        for _ in range(1, member_count):
            child_gender = pick_gender()

            edge_roll = random.random()
            if edge_roll < 0.015:
                child_given = random.choice(EDGE_SHORT_NAMES)
            elif edge_roll < 0.025:
                child_given = random.choice(EDGE_APOSTROPHE_NAMES)
            elif edge_roll < 0.035:
                child_given = random.choice(GENDER_AMBIGUOUS_NAMES)
            else:
                child_given = pick_given_name(child_gender)

            child_family = head_family
            child_dob = gen_dob(0, 60)
            child_father = head_given if head_gender == "MALE" else head_father

            c_lat, c_lon, c_acc = gps_variant(lat, lon, acc)

            child_ref, child_idx = store.add_individual(
                child_given, child_family, child_gender, child_dob,
                child_father, None, boundary, c_lat, c_lon, c_acc,
                is_child=True
            )
            store.add_hh_member(hh_ref, child_ref, is_head=False)
            store.add_project_beneficiary(child_ref)
            originals.append((child_idx, child_given, child_family, child_gender,
                              child_dob, child_father, boundary, c_lat, c_lon, c_acc))
            created += 1

        if created % 5000 == 0 or created == NUM_UNIQUE_INDIVIDUALS:
            progress(min(created, NUM_UNIQUE_INDIVIDUALS), NUM_UNIQUE_INDIVIDUALS,
                     "Individuals")

    print(f"  Created {len(store.households)} households")

    # --- Create deliberate duplicates ---
    print(f"Creating {NUM_DUPLICATE_PAIRS} duplicate pairs...")
    dup_sources = random.sample(originals, min(NUM_DUPLICATE_PAIRS, len(originals)))

    for i, src in enumerate(dup_sources):
        src_idx, src_given, src_family, src_gender, src_dob, \
            src_father, src_boundary, src_lat, src_lon, src_acc = src

        new_given, new_family, new_dob, new_father, \
            new_lat, new_lon, new_acc, new_boundary, var_type = make_variant(
                src_given, src_family, src_gender, src_dob, src_father,
                src_lat, src_lon, src_acc, src_boundary
            )

        dup_ref, dup_idx = store.add_individual(
            new_given, new_family, src_gender, new_dob,
            new_father, None, new_boundary,
            new_lat, new_lon, new_acc,
            phone=gen_phone() if random.random() < 0.3 else None,
            is_child=True
        )

        # Assign to a random household
        store.add_hh_member(random.choice(hh_refs), dup_ref, is_head=False)
        store.add_project_beneficiary(dup_ref)

        if (i + 1) % 500 == 0 or i + 1 == NUM_DUPLICATE_PAIRS:
            progress(i + 1, NUM_DUPLICATE_PAIRS, "Duplicates")

    total = len(store.individuals)
    print(f"\n  Total: {total} individuals, {len(store.households)} households, "
          f"{len(store.household_members)} HH-members, "
          f"{len(store.project_beneficiaries)} beneficiaries")
    return store


# ============================================================
# SQL WRITERS (Batch INSERT for performance)
# ============================================================

def write_batch_inserts(f, table, columns, rows, batch_size=SQL_BATCH_SIZE):
    """Write batch INSERT statements"""
    cols = ", ".join(columns)
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        f.write(f"INSERT INTO {table} ({cols}) VALUES\n")
        for j, row in enumerate(batch):
            vals = ", ".join(row)
            comma = "," if j < len(batch) - 1 else ";"
            f.write(f"  ({vals}){comma}\n")
        f.write("\n")


def write_schema(path):
    sql = """-- ============================================================
-- HCM Synthetic Dataset - Schema (v2 - 55K Scale)
-- Matches transformer_config.dart data model
-- ============================================================

DROP TABLE IF EXISTS project_beneficiary CASCADE;
DROP TABLE IF EXISTS household_member CASCADE;
DROP TABLE IF EXISTS individual_identifier CASCADE;
DROP TABLE IF EXISTS individual_address CASCADE;
DROP TABLE IF EXISTS individual_name CASCADE;
DROP TABLE IF EXISTS individual CASCADE;
DROP TABLE IF EXISTS household_address CASCADE;
DROP TABLE IF EXISTS household CASCADE;

CREATE TABLE household (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    member_count INTEGER DEFAULT 1,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    household_type VARCHAR(32) DEFAULT 'FAMILY',
    children_count INTEGER DEFAULT 0,
    pregnant_women_count INTEGER DEFAULT 0,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE household_address (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    related_client_reference_id UUID NOT NULL REFERENCES household(client_reference_id),
    door_no VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location_accuracy DOUBLE PRECISION,
    address_line1 TEXT,
    address_line2 TEXT,
    type VARCHAR(32) DEFAULT 'PERMANENT',
    locality_code VARCHAR(256),
    locality_name VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE individual (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    date_of_birth DATE,
    mobile_number VARCHAR(32),
    father_name VARCHAR(256),
    husband_name VARCHAR(256),
    gender VARCHAR(16),
    boundary_code VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE individual_name (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    individual_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    given_name VARCHAR(256) NOT NULL,
    family_name VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP
);

CREATE TABLE individual_address (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    related_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    door_no VARCHAR(32),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    location_accuracy DOUBLE PRECISION,
    address_line1 TEXT,
    address_line2 TEXT,
    type VARCHAR(32) DEFAULT 'PERMANENT',
    locality_code VARCHAR(256),
    locality_name VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE individual_identifier (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    individual_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    identifier_type VARCHAR(64),
    identifier_id VARCHAR(256),
    boundary_code VARCHAR(256),
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP
);

CREATE TABLE household_member (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    household_client_reference_id UUID NOT NULL REFERENCES household(client_reference_id),
    individual_client_reference_id UUID NOT NULL REFERENCES individual(client_reference_id),
    is_head_of_household BOOLEAN DEFAULT FALSE,
    tenant_id VARCHAR(64) NOT NULL,
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

CREATE TABLE project_beneficiary (
    id SERIAL PRIMARY KEY,
    client_reference_id UUID NOT NULL UNIQUE,
    project_id VARCHAR(128) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    beneficiary_client_reference_id UUID NOT NULL,
    date_of_registration TIMESTAMP,
    tag VARCHAR(256),
    row_version INTEGER DEFAULT 1,
    created_by VARCHAR(128) DEFAULT 'synthetic-gen',
    created_time TIMESTAMP,
    last_modified_by VARCHAR(128) DEFAULT 'synthetic-gen',
    last_modified_time TIMESTAMP
);

-- Performance indexes
CREATE INDEX idx_ind_name_given ON individual_name(given_name);
CREATE INDEX idx_ind_name_family ON individual_name(family_name);
CREATE INDEX idx_ind_gender ON individual(gender);
CREATE INDEX idx_ind_boundary ON individual(boundary_code);
CREATE INDEX idx_ind_dob ON individual(date_of_birth);
CREATE INDEX idx_ind_father ON individual(father_name);
CREATE INDEX idx_hm_hh ON household_member(household_client_reference_id);
CREATE INDEX idx_hm_ind ON household_member(individual_client_reference_id);
CREATE INDEX idx_pb_benef ON project_beneficiary(beneficiary_client_reference_id);
CREATE INDEX idx_pb_project ON project_beneficiary(project_id);
CREATE INDEX idx_ind_addr_loc ON individual_address(locality_code);
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"  01_schema.sql")


def write_data(store, out_dir):

    # --- Households ---
    path = os.path.join(out_dir, "02_households.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Households: {len(store.households)} records\n\n")
        rows = []
        for h in store.households:
            rows.append([
                sql_val(h["ref"]), str(h["memberCount"]),
                str(h["lat"]), str(h["lon"]),
                sql_val(h["tenantId"]), "1", sql_val(h["householdType"]),
                str(h["childrenCount"]), str(h["pregnantCount"]),
                sql_val(h["ts"]), sql_val(h["ts"]),
            ])
        write_batch_inserts(f, "household",
            ["client_reference_id", "member_count", "latitude", "longitude",
             "tenant_id", "row_version", "household_type",
             "children_count", "pregnant_women_count",
             "created_time", "last_modified_time"],
            rows)
    print(f"  02_households.sql ({len(store.households)} rows)")

    # --- Household addresses ---
    path = os.path.join(out_dir, "03_household_addresses.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Household Addresses: {len(store.household_addresses)} records\n\n")
        rows = []
        for a in store.household_addresses:
            rows.append([
                sql_val(a["ref"]), sql_val(a["hhRef"]),
                sql_val(a["doorNo"]), str(a["lat"]), str(a["lon"]), str(a["acc"]),
                sql_val(a["addr1"]), sql_val(a["addr2"]),
                "'PERMANENT'", sql_val(a["locCode"]), sql_val(a["locName"]),
                sql_val(a["tenantId"]), "1",
                sql_val(a["ts"]), sql_val(a["ts"]),
            ])
        write_batch_inserts(f, "household_address",
            ["client_reference_id", "related_client_reference_id",
             "door_no", "latitude", "longitude", "location_accuracy",
             "address_line1", "address_line2", "type",
             "locality_code", "locality_name",
             "tenant_id", "row_version",
             "created_time", "last_modified_time"],
            rows)
    print(f"  03_household_addresses.sql ({len(store.household_addresses)} rows)")

    # --- Individuals ---
    path = os.path.join(out_dir, "04_individuals.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Individuals: {len(store.individuals)} records\n\n")
        rows = []
        for ind in store.individuals:
            rows.append([
                sql_val(ind["ref"]), sql_val(ind["dob"]),
                sql_val(ind["phone"]), sql_val(ind["father"]),
                sql_val(ind["husband"]), sql_val(ind["gender"]),
                sql_val(ind["boundaryCode"]), sql_val(ind["tenantId"]),
                "1", sql_val(ind["ts"]), sql_val(ind["ts"]),
            ])
        write_batch_inserts(f, "individual",
            ["client_reference_id", "date_of_birth", "mobile_number",
             "father_name", "husband_name", "gender", "boundary_code",
             "tenant_id", "row_version", "created_time", "last_modified_time"],
            rows)
    print(f"  04_individuals.sql ({len(store.individuals)} rows)")

    # --- Individual names ---
    path = os.path.join(out_dir, "05_individual_names.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Individual Names: {len(store.individual_names)} records\n\n")
        rows = []
        for n in store.individual_names:
            rows.append([
                sql_val(n["ref"]), sql_val(n["indRef"]),
                sql_val(n["given"]), sql_val(n["family"]),
                sql_val(n["tenantId"]), "1", sql_val(n["ts"]),
            ])
        write_batch_inserts(f, "individual_name",
            ["client_reference_id", "individual_client_reference_id",
             "given_name", "family_name",
             "tenant_id", "row_version", "created_time"],
            rows)
    print(f"  05_individual_names.sql ({len(store.individual_names)} rows)")

    # --- Individual addresses ---
    path = os.path.join(out_dir, "06_individual_addresses.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Individual Addresses: {len(store.individual_addresses)} records\n\n")
        rows = []
        for a in store.individual_addresses:
            rows.append([
                sql_val(a["ref"]), sql_val(a["indRef"]),
                sql_val(a["doorNo"]), str(a["lat"]), str(a["lon"]), str(a["acc"]),
                sql_val(a["addr1"]), sql_val(a["addr2"]),
                "'PERMANENT'", sql_val(a["locCode"]), sql_val(a["locName"]),
                sql_val(a["tenantId"]), "1",
                sql_val(a["ts"]), sql_val(a["ts"]),
            ])
        write_batch_inserts(f, "individual_address",
            ["client_reference_id", "related_client_reference_id",
             "door_no", "latitude", "longitude", "location_accuracy",
             "address_line1", "address_line2", "type",
             "locality_code", "locality_name",
             "tenant_id", "row_version",
             "created_time", "last_modified_time"],
            rows)
    print(f"  06_individual_addresses.sql ({len(store.individual_addresses)} rows)")

    # --- Individual identifiers ---
    path = os.path.join(out_dir, "07_individual_identifiers.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Individual Identifiers: {len(store.individual_identifiers)} records\n\n")
        rows = []
        for ident in store.individual_identifiers:
            rows.append([
                sql_val(ident["ref"]), sql_val(ident["indRef"]),
                sql_val(ident["idType"]), sql_val(ident["idValue"]),
                sql_val(ident["boundaryCode"]), sql_val(ident["tenantId"]),
                "1", sql_val(ident["ts"]),
            ])
        write_batch_inserts(f, "individual_identifier",
            ["client_reference_id", "individual_client_reference_id",
             "identifier_type", "identifier_id", "boundary_code",
             "tenant_id", "row_version", "created_time"],
            rows)
    print(f"  07_individual_identifiers.sql ({len(store.individual_identifiers)} rows)")

    # --- Household members ---
    path = os.path.join(out_dir, "08_household_members.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Household Members: {len(store.household_members)} records\n\n")
        rows = []
        for hm in store.household_members:
            rows.append([
                sql_val(hm["ref"]), sql_val(hm["hhRef"]), sql_val(hm["indRef"]),
                sql_bool(hm["isHead"]), sql_val(hm["tenantId"]),
                "1", sql_val(hm["ts"]), sql_val(hm["ts"]),
            ])
        write_batch_inserts(f, "household_member",
            ["client_reference_id", "household_client_reference_id",
             "individual_client_reference_id", "is_head_of_household",
             "tenant_id", "row_version", "created_time", "last_modified_time"],
            rows)
    print(f"  08_household_members.sql ({len(store.household_members)} rows)")

    # --- Project beneficiaries ---
    path = os.path.join(out_dir, "09_project_beneficiaries.sql")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"-- Project Beneficiaries: {len(store.project_beneficiaries)} records\n\n")
        rows = []
        for pb in store.project_beneficiaries:
            rows.append([
                sql_val(pb["ref"]), sql_val(pb["projectId"]),
                sql_val(pb["tenantId"]), sql_val(pb["benefRef"]),
                sql_val(pb["regDate"]), "NULL",
                "1", sql_val(pb["ts"]), sql_val(pb["ts"]),
            ])
        write_batch_inserts(f, "project_beneficiary",
            ["client_reference_id", "project_id", "tenant_id",
             "beneficiary_client_reference_id", "date_of_registration",
             "tag", "row_version", "created_time", "last_modified_time"],
            rows)
    print(f"  09_project_beneficiaries.sql ({len(store.project_beneficiaries)} rows)")



def write_csvs(store, out_dir):
    # Flat individuals CSV
    path = os.path.join(out_dir, "individuals_flat.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["individual_client_ref", "given_name", "family_name", "gender",
                     "date_of_birth", "father_name", "husband_name", "mobile_number",
                     "boundary_code", "latitude", "longitude", "location_accuracy",
                     "locality_name", "tenant_id"])
        for i, ind in enumerate(store.individuals):
            n = store.individual_names[i]
            a = store.individual_addresses[i]
            w.writerow([
                ind["ref"], n["given"], n.get("family", ""), ind["gender"],
                ind["dob"], ind["father"], ind.get("husband", ""),
                ind.get("phone", ""), ind["boundaryCode"],
                a["lat"], a["lon"], a["acc"], a["locName"],
                ind["tenantId"]
            ])
    print(f"  individuals_flat.csv")



def write_readme(store, out_dir):
    path = os.path.join(out_dir, "DATASET_README.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""# HCM Synthetic Dataset (v2 - 55K Scale)

## Overview
Synthetic beneficiary registration data mimicking the DIGIT HCM production data model.
Data represents a Polio campaign in N'Djamena, Chad with African names
(Arabic-influenced, French-influenced, Sara/Kanuri/Hausa local names).

## Statistics
| Table | Records |
|-------|---------|
| Household | {len(store.households):,} |
| Individual | {len(store.individuals):,} |
| Individual Name | {len(store.individual_names):,} |
| Individual Address | {len(store.individual_addresses):,} |
| Individual Identifier | {len(store.individual_identifiers):,} |
| Household Member | {len(store.household_members):,} |
| Project Beneficiary | {len(store.project_beneficiaries):,} |

## Data Model (from transformer_config.dart)
```
Household --< HouseholdMember >-- Individual
                                      |
                               IndividualName (givenName + familyName)
                               IndividualAddress (GPS + boundary)
                               IndividualIdentifier
                                      |
                               ProjectBeneficiary --> Campaign (projectId)
```

## Registration Flow
1. **Household** is created with GPS location and boundary assignment
2. **Individual** is registered with name (givenName + familyName), DOB, gender
3. **HouseholdMember** links the individual to the household
4. **ProjectBeneficiary** links the individual to the campaign (projectId)

## Name Characteristics
- **Arabic-influenced**: Mahamat, Ibrahim, Abubakar, Fatima, Amina, Khadija
- **French-influenced**: Jean-Pierre, Francois, Christine, Therese
- **Local/Sara/Kanuri**: Nadjitangar, Djimadoum, Ngarmbatina, Koubra
- **Hausa/Fulani**: Bukar, Modu, Bello, Garba, Shehu

## Files
### SQL Files (execute in order)
1. `01_schema.sql` - CREATE TABLE statements with indexes
2. `02_households.sql` - Household records
3. `03_household_addresses.sql` - Household addresses with GPS
4. `04_individuals.sql` - Individual records
5. `05_individual_names.sql` - Individual names (givenName + familyName)
6. `06_individual_addresses.sql` - Individual addresses with GPS + boundary
7. `07_individual_identifiers.sql` - Individual identifiers
8. `08_household_members.sql` - Household-Individual links
9. `09_project_beneficiaries.sql` - Campaign beneficiary links

### CSV
- `individuals_flat.csv` - All individuals flattened with name, GPS, boundary

## Loading into PostgreSQL
```bash
psql -d your_db -f 01_schema.sql
for i in 02 03 04 05 06 07 08 09; do
  psql -d your_db -f ${{i}}_*.sql
done
```

## Loading CSV in Python
```python
import pandas as pd
individuals = pd.read_csv('individuals_flat.csv')
```

## Configuration
- Campaign: {PROJECT_ID}
- Region: N'Djamena, Chad
- Boundary Source: POLIO_CHAD.xlsx (45 settlement boundaries)
- GPS Center: {BASE_LAT}, {BASE_LON}
- Seed: {SEED}
""")
    print(f"  DATASET_README.md")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("HCM Synthetic Dataset Generator v2 (55K Scale)")
    print("=" * 60)
    print()

    store = generate()

    print("\nWriting SQL files (batch inserts)...")
    write_schema(os.path.join(out_dir, "01_schema.sql"))
    write_data(store, out_dir)

    print("\nWriting CSV files...")
    write_csvs(store, out_dir)

    print("\nWriting documentation...")
    write_readme(store, out_dir)

    # File size report
    print("\nFile sizes:")
    total = 0
    for fn in sorted(os.listdir(out_dir)):
        if fn.endswith((".sql", ".csv", ".md")):
            sz = os.path.getsize(os.path.join(out_dir, fn))
            total += sz
            if sz > 1024*1024:
                print(f"  {fn:45s} {sz/1024/1024:.1f} MB")
            else:
                print(f"  {fn:45s} {sz/1024:.0f} KB")
    print(f"  {'TOTAL':45s} {total/1024/1024:.1f} MB")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

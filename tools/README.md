# Narzędzia pomocnicze

## Kontrola polskich znaków

W projekcie obowiązuje zasada: **cały tekst po polsku ma pełne znaki
diakrytyczne** — w komentarzach, dokumentacji, komunikatach programu
i na wydrukach kart.

Sprawdzenie, czy gdzieś nie wkradł się zapis bez ogonków:

```bash
python tools/check_polish.py
```

Automatyczna poprawa (dopasowanie całymi wyrazami, z zachowaniem wielkości
liter — „zrodlo" → „źródło", „PODGLAD" → „PODGLĄD"):

```bash
python tools/fix_polish.py --dry    # najpierw podgląd zmian
python tools/fix_polish.py          # zastosowanie
```

Słownik poprawek jest w `polish_words.py`. Dopasowanie działa na **całych
wyrazach**, więc „pytan" → „pytań", ale „pytania" pozostaje nietknięte.
Wyrazy z listy `NEVER_TOUCH` (np. nazwa pliku `przyklad.json`) są chronione.

### Ograniczenia

Narzędzie poprawia pisownię wyrazów, ale nie odmianę. Błędy w rodzaju
„adnotowana klatkę" zamiast „adnotowaną klatkę" trzeba wyłapać samodzielnie
— warto po każdej większej zmianie przejrzeć teksty widoczne dla użytkownika.

### Uwaga o plikach `.ps1`

Skrypty PowerShella zapisujemy w **UTF-8 z BOM**. Bez BOM Windows
PowerShell 5.1 błędnie interpretuje polskie znaki i wypisuje krzaki.

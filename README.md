# Odporność na bessy: badanie historyczne

Badanie sprawdza, jakie spółki i ETF-y (UCITS, dostępne w XTB) najlepiej broniły się w bessach S&P 500 od 1962 roku. Autor chciał przygotować się na możliwą bessę, a nie reagować na trwającą.

Strona z wynikami (opowieść w 7 krokach): https://majsterkovic.github.io/bessy-odpornosc/

Pełny raport: [docs/raport.md](docs/raport.md).

## Uwaga

To materiał badawczy i edukacyjny, a nie porada inwestycyjna ani rekomendacja zakupu. Wyniki dotyczą spółek notowanych dziś (błąd przeżywalności), są liczone w USD i opierają się na kilkunastu bessach. Listy to kandydaci do sprawdzenia. Dostępność w XTB trzeba zweryfikować przed zakupem.

## Zawartość

- `bessy/`: kod badania w Pythonie (odczyt z lokalnej bazy Postgres `marketdata`, tylko do odczytu).
- `tests/`: testy kodu badania (`pytest`).
- `web/`: statyczna strona (Vite, React, TypeScript, ECharts). Dane to migawka w `web/public/data/`.
- `docs/raport.md`: raport z wynikami.

Baza z notowaniami i klucze do API nie są częścią repozytorium. Aby przeliczyć badanie, trzeba mieć własną bazę i plik `.env` z `PG_DSN`. Szczegóły uruchomienia strony: [web/README.md](web/README.md).

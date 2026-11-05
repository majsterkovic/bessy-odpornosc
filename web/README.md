# Bessy: strona z wynikami badania

Statyczna strona (Vite, React, TypeScript, ECharts), która opowiada badanie odporności na bessy w 7 krokach i kończy się listami Top.
Czyta tylko pliki JSON z `public/data/`. Nie łączy się z bazą.

## Uruchomienie

```bash
.venv/bin/python -m bessy.run --as-of 2026-10-26 --out ../docs/raport.md   # tylko gdy trzeba przeliczyć badanie
.venv/bin/python -m bessy.export_web      # zapisuje web/public/data/*.json (baza tylko do odczytu)
cd web && npm install && npm run dev      # http://localhost:5173 (serwer słucha na wszystkich interfejsach, bo przeglądarka bywa w Windowsie)
```

Wersja produkcyjna: `npm run build && npm run preview` (http://localhost:4173). Strona ma adres bazowy względny, ale nie działa przez `file://`.

## Testy

`npm test` (Vitest, dane próbne w `src/testData.ts`) oraz `cd .. && .venv/bin/pytest -q` (eksporter).

## Uwaga

Pliki w `public/data/` to migawka wyników z 2026-10-26 (ostatnie notowania w bazie). Nie zawierają sekretów, a test eksportera to sprawdza.
Strona pokazuje kandydatów do sprawdzenia, nie rekomendację zakupu.

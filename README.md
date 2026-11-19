# Csengő vezérlőpult

Színes termináls felület (TUI) az iskolai csengő kezeléséhez.

## Telepítés

```powershell
pip install -r requirements.txt
```

## Indítás

```powershell
python tui.py
```

## Lehetőségek a felületen

| Vezérlő | Mit csinál |
|---|---|
| **Csengő: KI/BE** kapcsoló | elindítja / leállítja a háttérben futó csengő folyamatot |
| **▶ Indítás / ■ Leállítás** | ugyanaz gombokkal |
| **↻ Újratöltés** | újraolvassa a beállítás- és órarendfájlokat |
| **◈ Próba csengés** | lejátssza a kijelölt időponthoz tartozó hangot |
| **Óratípus** | **Normál órák** (alapértelmezett) és **Rövidített órák** között vált |
| **Időpont + Hang → ＋ Hozzáadás** | új KI/BE csengés felvétele – *meglévő időpontot nem enged felvenni* |
| **✎ Módosítás** | a kijelölt sor időpontjának és hangjának átírása (ütközést itt is tilt) |
| **✕ Törlés** | a kijelölt időpont törlése |
| **Hangok / Alkalmaz** | a kijelölt időponthoz rendeli a hangfájlt |
| **▶ Hallgasd** | meghallgatás |
| **Napi bekapcsolás** | napok ki/be kapcsolása (zöld = csörög, szürke = nem) |

## Billentyűk

`Ctrl+S` Ki/Bekapcsolás · `Ctrl+T` Óratípus · `Ctrl+R` Újratöltés · `Ctrl+P` Próba csengés · `Ctrl+Q` Kilépés

## Fájlok

- `settings.json` – óratípus (`normal` / `rovid`) és alapértelmezett hang
- `normal.json`, `rovid.json` – `<időpont>: <hangfájl>` párok
- `days.json` – mely napokon csörögjön (1/0)
- `csengeto.log` – a csengő naplója
- `csenget.py` – a háttérfolyamat; a felület indítja/állítja le

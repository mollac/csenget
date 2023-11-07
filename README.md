# csenget
ki- becsengető script

Használat: python csenget.py

Működése: ha nem adunk meg paramétert, a normal.json fájlt olvassa be, ami a ki- illetve a becsengetések idejét tartalmazza 
valamint az adott időponthoz rendelt mp3 fájlt.

A rovid.json a nálunk használt rövidített órák csengetési rendjét használja, ekkor az indítás: python csenget.py rovid.json
 
A days.json fájl, amiben a nap neve mellett az 1 vagy 0 lehet.

 1 - csenget azon a napon
  
 0 - nem csenget azon a napon

A json fájlok tetszőlegesen átírhatók, a formátum azonban fontos.
Akár minden időponthoz lehet más mp3-at rendelni, vagy sorokat
törölni, ha kevesebb időpont van.

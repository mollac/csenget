# csenget
ki- becsengető script

Használat: python csenget.py

Működése: ha nem adunk meg paramétert, a normal.json fájlt olvassa be, ami a ki- illetve a becsengetések idejét tartalmazza 
valamint az adott időponthoz rendelt mp3 fájlt.

A rovid.json a nálunk használt rövidített órák csengetési rendjét használja, ekkor az indítás: python csenget.py rovid.json

A json fájlok tetszőlegesen átírhatók, a formátum azonban fontos.
Akár minden időponthoz lehet más mp3-at rendelni, vagy sorokat
törölni, ha kevesebb időpont van.

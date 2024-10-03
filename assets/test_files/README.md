# Sample files with collections

This directory contains a few sample collections from various Wikipedia projects.

* `10chapter.json`- A collection of 10 random articles containing chapters.
* `10random.json`- A collection of 10 random articles.
* `amphibious_aircraft.json`- PediaPress showcase book - A collection of articles about amphibious aircraft
* `bengali.json`- WPEN article "Bengali Alphabet"
* `chinese_script.json`- WPEN article "Chinese script styles"
* `element.json`- WPEN article "Chemical element"
* `fonts.json`- WPEN collection containing various fonts and writing systems to test i18n support
* `hogwarts_express.json`- WPEN article "Hogwarts Express (Universal Orlando Resort)"
* `i18n_math.json`- WPEN collection with various challenging i18n and math articles
* `iotation.json`- WPEN article "Iotation"
* `local_cities.json`- WPDE collection with articles about local cities (in German)
* `premier.json`- WPEN article "Premier League" containing complex tables
* `san_francisco.json`- WPEN article "San Francisco"
* `schroedinger.json`- WPEN article "Schrödinger equation"
* `the_nether_world.json`- WikiSource collection "The Nether World" using the ProofreadPage extension
* `wiesbaden.json`- WPDE article "Wiesbaden"
* `wpeu_100_articles.json`- WPEU collection of 100 articles from the Basque Wikipedia
* `wpeu_begonako_errepublika.json`- WPEU article "Begonako Errepublika"
* `wpeu_person.json`- WPEU article "Jose Ramon Etxebarria"

## Rendering

Use `mw-zip` to create a ZIP archive of a collection for rendering. For example:

```bash
mw-zip -c "https://en.wikipedia.org/w" -o 10chapter.zip -m 10chapter.json
```

To render the collection use `mw-render`:

```bash
mw-render -w pdf -o 10chapter.pdf -c 10chapter.zip
```

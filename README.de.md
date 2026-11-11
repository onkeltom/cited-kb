<p align="center">
  <a href="README.md">English</a> ·
  <strong>Deutsch</strong> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.es.md">Español</a>
</p>

<div align="center">
<pre>
 ██████╗██╗████████╗███████╗██████╗ 
██╔════╝██║╚══██╔══╝██╔════╝██╔══██╗
██║     ██║   ██║   █████╗  ██║  ██║
██║     ██║   ██║   ██╔══╝  ██║  ██║
╚██████╗██║   ██║   ███████╗██████╔╝
 ╚═════╝╚═╝   ╚═╝   ╚══════╝╚═════╝ 
</pre>

<p>Podcasts und Talks rein. Eine Wissensbasis, aus der du lernst.</p>

<p>Embeddings schlagen vor. Ein Mensch nimmt an.</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="MIT-Lizenz" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="Transkripte bleiben auf deinem Rechner" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">Schnellstart</a> ·
  <a href="#the-loop">Der Ablauf</a> ·
  <a href="#human-work">Die menschliche Arbeit</a> ·
  <a href="#recall">Zurückgehen</a> ·
  <a href="#later">Später</a> ·
  <a href="#layout">Aufbau</a>
</p>
</div>

---

<h2 id="quick-start">Schnellstart</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

Python 3.9 oder neuer, mit SQLite FTS5 (die üblichen Builds von macOS und python.org). Die Fixture ist synthetisch, der Lauf braucht also noch keinen echten Mitschnitt. Whisper und der Tagger sind optional. Beides steht unten.

<h2 id="the-loop">Der Ablauf</h2>

```text
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  sources │───▶│   cards  │───▶│   index  │───▶│ propose  │
└──────────┘    └──────────┘    └──────────┘    └────┬─────┘
                                                     │
                                                     ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  recall  │◀───│   brief  │◀───│ packets  │◀───│   walk   │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

`propose` schreibt Kandidaten. `walk` ist die Stelle, an der ein Tag zu dem wird, was du weißt. Nur angenommene Tags kommen in ein Packet. `brief` ist, wie du dich wieder zu einer Frage setzt, ohne die Folgen noch einmal zu hören.

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

Ein Agent darf Karten entwerfen und eine Frage aus einem Brief wieder hervorholen. Er darf kein Tag annehmen, keine Kategorie erfinden und kein ganzes Transkript lesen, um zusammenzufassen, was du gelernt hast. Die kurze Fassung steht in [`AGENT.md`](AGENT.md) (Englisch, die Regeln sind dieselben).

<h2 id="what-this-is">Was das ist</h2>

| Das ist es | Das ist es nicht |
|---|---|
| Eine lokale Wissensbasis zum Lernen: aus Podcasts und Talks werden Claims, zu denen du zurückkehrst | Ein gehostetes Corpus oder der fertige Kurs von jemand anderem |
| Dünne Karten und ein Index, damit du die Aufnahme nicht noch einmal hörst | Eine Zusammenfassungsmaschine |
| Ein Codebook, das du schreibst, und danach ein Vorschlager | Ein Auto-Tagger |
| Ein menschlicher Walk, dann Packets, die du wieder aufschlägst | Eine App, die Open Coding für dich erledigt |

<h2 id="rights">Rechte</h2>

Transkripte bleiben auf dem Rechner, der sie geholt hat. Du brauchst das Recht, sie zu behalten. Committe nicht die Worte anderer Leute. Dieses Repo liefert eine synthetische Fixture und ein leeres Domain-Pack. Deine Quellen, Karten und Tags gehören dir, in deine eigene private Arbeitskopie.

<h2 id="setup">Einrichtung</h2>

<h3 id="setup-video">Video</h3>

`yt-dlp` und `youtube-transcript-api` aus dem Schnellstart reichen für Untertitel. Wenn YouTube eine Anmeldung verlangt, häng `--cookies-from-browser chrome` an `cited.py add`. Geht ein Abruf nach einer Änderung der Seite kaputt, aktualisiere `yt-dlp`.

<h3 id="setup-podcasts">Podcasts</h3>

Feeds mit mitgeliefertem Transkript werden so verwendet. Sonst wird das Audio lokal transkribiert. Es wird nichts hochgeladen.

```bash
# Apple Silicon
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# überall sonst
python3 -m pip install -U faster-whisper
```

Die erste Transkription lädt ein Whisper-Modell (etwa 1,5 GB). Den Wortschatz setzt du in `domain/whisper_prompt.txt`. Der Beispielprompt ist allgemein. Ersetze ihn durch die Eigennamen deines Feldes, sonst werden sie falsch gehört.

<h3 id="setup-tagging">Tagging</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# BAAI/bge-small-en-v1.5 nach models/bge-small laden
# (MIT). Die Gewichte liegen nicht in diesem Repo.
```

`cited.py mine propose` nutzt dieses lokale Modell. Ohne das Modell funktionieren Suche, Karten und Briefs weiter. Du taggst von Hand, oder du installierst das Modell.

<h3 id="setup-domain">Dein Domain-Pack</h3>

```bash
cp -R domain.example domain
```

Vier Dinge bearbeiten, bevor du in großem Stil taggst:

- `domain/categories.json` — id, name, definition, aliases. Die zwei Beispiele sind Platzhalter.
- `domain/card.json` — Topics und die geschlossenen Vokabulare einer Karte.
- `domain/layer1.md` — ein Absatz: was du zu dieser Frage gerade hältst, und was nicht.
- `domain/whisper_prompt.txt` — Namen und Begriffe, die der Transkriber erwarten soll.

<h2 id="first-hour">Die erste Stunde</h2>

1. Schnellstart laufen lassen und prüfen, dass die Fixture suchbar ist.
2. Eine Quelle holen, zu der du das Recht hast. Erst listen, dann laden.

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests`, dann `python3 cited.py meta <id> --guest "…" --role "…" --company "…"`, bis die Fragezeichen weg sind.
4. Aufhören. Die Karte schreiben. Noch nicht `propose`.

<h2 id="human-work">Die menschliche Arbeit</h2>

Die Befehle laufen auch mit einer leeren Theorie und einem Stapel Folgen, zu denen du nie zurückkehrst. Diese Schritte machen die Basis zu etwas, woraus du lernst. Jeder hat einen fertigen Zustand. Lässt du ihn aus, ist der Fehler konkret.

<details>
<summary><b>1 · Linse</b> — die Frage schreiben, bevor du lädst</summary>

<br>

Schreib die Frage, dann die Regeln für das, was hinein darf: es trägt zur Frage bei, Rückblicke und Best-ofs bleiben draußen, derselbe Gast kommt höchstens zweimal vor, widersprechende Stimmen bleiben drin.

Fertig, wenn jemand anders die Regeln auf eine neue Folge anwenden könnte.

Ohne das ist das Corpus das, was der Feed veröffentlicht hat.

</details>

<details>
<summary><b>2 · Ingest</b> — erst listen, dann holen, die Show taggen</summary>

<br>

Zuerst `pod --list` oder `queue`. Die Show beim Reinholen taggen.

Fertig, wenn jede Datei in `transcripts/` eine ist, die du verkarten willst.

Ohne das transkribierst du Stunden, die du nie encodierst.

</details>

<details>
<summary><b>3 · Namen</b> — Spracherkennung lügt bei Menschen und Zahlen</summary>

<br>

`cited.py guests`, dann `cited.py meta` für jedes `?`. Namen und Zahlen gegen die Shownotes prüfen.

Fertig, wenn ein Beleg die richtige Person nennen würde.

Ohne das schreibst du den Kredit der falschen Person zu.

</details>

<details>
<summary><b>4 · Dünne Karten</b> — die Karte ist der Beleg, das Transkript die Prüfung</summary>

<br>

Ein Agent darf aus `cited.py card-scaffold` entwerfen. Du lässt `validate_cards.py` laufen. Paraphrasieren. Jeder Zeitstempel muss ein Absatzanfang im Transkript sein. Höchstens zwei Zitate, kurz und wörtlich.

Fertig, wenn der Validator still ist und `reindex` die neuen Claims zeigt.

Ohne das ist der Index Fiktion.

</details>

<details>
<summary><b>5 · Codebook</b> — aus deinen Quellen schreiben, dann propose anschalten</summary>

<br>

Lies etwa fünfzehn Quellen. Schreib die Kategorien in deinen eigenen Worten: id, name, definition, aliases. Tagge eine Stichprobe von Hand. Ein voller Open-Coding-Durchgang ist ein eigenes Vorhaben, und ein teures. Die Platzhalter in `domain.example` sind keine Theorie.

Fertig, wenn du jede Kategorie erklären kannst, ohne auf einen Score zu sehen.

Ohne das taggst du das Corpus mit den Beispielen oder mit der Frage von jemand anderem.

</details>

<details>
<summary><b>6 · Kalibrieren</b> — unklare Kategorien verlassen die Standard-Warteschlange</summary>

<br>

Markiere jede Kategorie in `domain/calibration.jsonl` als clear, fuzzy oder unclear. Unclear bleibt aus `mine walk` draußen, außer du gibst `--include-unclear`.

Fertig, wenn die Warteschlange nur Kategorien enthält, die du anwenden kannst.

Ohne das versinkt die Review-Zeit in solchen, die du nicht anwenden kannst.

</details>

<details>
<summary><b>7 · Walk</b> — annehmen ist eine menschliche Taste</summary>

<br>

<kbd>a</kbd> accept, <kbd>r</kbd> reject, <kbd>n</kbd> none, <kbd>s</kbd> skip, <kbd>q</kbd> quit. Unsicher heißt skip. Reject nur, wenn du Claim und Kategorie beide verstehst. Es gibt kein Massen-Accept.

Fertig, wenn du jede angenommene Zeile laut sagen würdest.

Ohne das sind die Zahlen die Meinung des Modells.

</details>

<details>
<summary><b>8 · Offenlegung</b> — ein Verkäufer wird kein unabhängiger Zeuge</summary>

<br>

Verkauft der Gast die Sache, um die es geht, oder ist die Folge gesponsert, bleibt dieses Flag auf jedem Beleg, der einen Befund trägt.

Fertig, wenn eine Vendor-Folge nicht als unabhängige Praxis gelesen werden kann.

Ohne das wird ein Verkaufsgespräch zum Beleg.

</details>

<details>
<summary><b>9 · Packets</b> — ein Packet pro Frage, die du lernst</summary>

<br>

Packets nur aus angenommenen Tags neu aufbauen. Das Anomalie-Packet ist der Pool der `none`. Dort schaust du hin, wenn ein Claim nicht gepasst hat. Es ist kein eigenes Thema.

Fertig, wenn `cited.py packet list` zu den Fragen passt, die du wirklich studierst.

Ohne das fängst du jedes Mal, wenn du dich erinnern willst, mit einer neuen Suche an.

</details>

<details>
<summary><b>10 · Lernen</b> — die Frage wieder aufschlagen, nicht den Ordner</summary>

<br>

`cited.py brief` sammelt die angenommenen Claims zu einer Frage. Das ist der Lerndurchgang. Suche nur, wenn dieses Packet dünn ist. Der Transkript-Ordner ist nicht der Kontext.

Fertig, wenn du die Frage aus dem Brief wiedergeben kannst, ohne eine Folge zu öffnen.

Ohne das hörst du noch einmal hin, oder du vertraust einer vagen Erinnerung.

</details>

<details>
<summary><b>11 · Drei Schichten</b> — trenne, was gesagt wurde, von dem, was du jetzt denkst</summary>

<br>

Wenn du dir eine Frage erklärst, halte drei Schichten auseinander: die Kategorien, die du eingefroren hast, die weiteren Folgen, und deine eigene Schlussfolgerung. Die dritte ist dein Lernen. Sie ist nichts, was die Gäste belegt haben.

Fertig, wenn du zeigen kannst, welcher Teil von dir ist.

Ohne das verhärtet sich eine Schlussfolgerung zu „das haben die Podcasts gesagt“.

</details>

<details>
<summary><b>12 · Nenner</b> — wisse, was du wirklich aufgenommen hast</summary>

<br>

`cited.py corpus` druckt, wie viele Folgen du geholt, wie viele du verkartet und wie viele Claims du angenommen hast. Das sind verschiedene Zahlen.

Fertig, wenn du sagen kannst, welche Zahl du meinst.

Ohne das fühlt sich ein Download-Ordner wie Können an.

</details>

<details>
<summary><b>13 · Drift</b> — eine neue Kategorie ist eine aufgeschriebene Entscheidung</summary>

<br>

Lies im festen Rhythmus die None-Rate, das Anomalie-Packet und die Gaps auf den Karten. Entscheide: halten, eine Definition schärfen, oder mit einer vorläufigen Kategorie erweitern. Die Entscheidung aufschreiben. Open Coding wieder zu öffnen ist eine eigene Entscheidung, kein Vorschlag des Werkzeugs, weil eine Folge seltsam war.

Fertig, wenn das Codebook eine datierte Notiz hat, auch wenn die Notiz „hold“ lautet.

Ohne das wird eine seltsame Folge zu einer neuen Kategorie.

</details>

<h2 id="recall">Zurückgehen</h2>

Wenn ein Punkt zählt, geh zurück zur Minute. `cited.py show <id> --at mm:ss --window 1`. Ein Zitat bleibt unter fünfzehn Wörtern. Nenne Person, Organisation und Show. Die Karte ist eine Paraphrase. Der Zeitstempel ist der Weg zurück.

<h2 id="later">Später</h2>

Die Basis ist für dein eigenes Lernen. Wenn eine Frage sitzt, taugen dieselben Packets für eine Notiz, einen Vortrag, eine Übergabe oder einen Kurs. Diese Verwendungen stehen in [`LATER.md`](LATER.md) (Englisch).

<h2 id="layout">Aufbau</h2>

```text
cited.py           der Befehl
domain.py          lädt dein Domain-Paket
validate_cards.py  Karten gegen Domain-Pack und Transkript
kbbert.py          lokale Embeddings, kein Torch
mining/            propose, walk, packets, brief
domain.example/    nach domain/ kopieren und bearbeiten
domain/            deine Kategorien, das Karten-Schema, Layer-1, der Prompt
examples/fixture/  synthetisches Transkript und eine Karte
transcripts/       deins, nicht für dieses öffentliche Repo
cards/             deins
AGENT.md           was ein Agent tun darf
LATER.md           Ideen, sobald eine Frage sitzt
```

`transcripts/`, `cards/`, `cited.sqlite` und `models/` sind in einer Arbeitskopie gitignored. `reindex` baut den Index aus den Dateien neu.

<h2 id="languages">Sprachen</h2>

Die Leiste oben ist der Sprachwechsel. Die Sprache, die du liest, ist Klartext. Die anderen sind Links. Englisch ist der Quelltext.

Eine Übersetzung ist eine Geschwisterdatei: `README.de.md`, `README.zh-CN.md`, `README.ja.md`, `README.ko.md`, `README.fr.md`, `README.es.md`. Prosa und Überschriften werden übersetzt. Befehle, Flags, Dateinamen, Kategorie-IDs und die Tasten <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd> nicht. Die Heading-IDs sind in jeder Datei dieselben, deshalb überlebt `#quick-start` den Sprachwechsel.

Für eine weitere Sprache `README.md` kopieren, die Prosa übersetzen, und diese Sprache in der eigenen Leiste mit `<strong>` markieren.

<h2 id="license">Lizenz</h2>

Der Code ist [MIT](LICENSE). Die BGE-Gewichte und die Whisper-Modelle sind eigene Downloads mit eigenen Lizenzen. Transkripte, die du holst, werden von diesem Projekt nicht neu lizenziert.

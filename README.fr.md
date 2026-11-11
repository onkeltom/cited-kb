<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <strong>Français</strong> ·
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

<p>Des podcasts et des talks en entrée. Une base pour apprendre.</p>

<p>Les plongements proposent. Une personne accepte.</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="licence MIT" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="Les transcriptions restent sur votre machine" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">Démarrage</a> ·
  <a href="#the-loop">La boucle</a> ·
  <a href="#human-work">Le travail humain</a> ·
  <a href="#recall">Revenir</a> ·
  <a href="#later">Ensuite</a> ·
  <a href="#layout">Agencement</a>
</p>
</div>

---

<h2 id="quick-start">Démarrage</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

Python 3.9 ou plus récent, avec SQLite FTS5 (les builds habituels de macOS et python.org). La fixture est synthétique : rien à télécharger pour ce premier passage. Whisper et le tagueur sont facultatifs. Leur mise en place est plus bas.

<h2 id="the-loop">La boucle</h2>

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

`propose` écrit des candidats. `walk` est l'endroit où un tag devient une part de ce que vous savez. Seuls les tags acceptés entrent dans un packet. `brief` est la façon de vous rasseoir avec une question, sans réécouter les épisodes.

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

Un agent peut rédiger une carte et rouvrir une question depuis un brief. Il n'accepte pas un tag, n'invente pas de catégorie, et ne lit pas une transcription entière pour résumer ce que vous avez appris. La version courte de ce contrat est [`AGENT.md`](AGENT.md) (en anglais, les règles sont les mêmes).

<h2 id="what-this-is">Ce que c'est</h2>

| C'est | Ce n'est pas |
|---|---|
| Une base locale pour apprendre : des podcasts et des talks deviennent des claims auxquels vous revenez | Un corpus hébergé, ou le cours déjà fait de quelqu'un d'autre |
| Des cartes minces et un index, pour ne plus réécouter l'enregistrement | Une machine à résumés |
| Un codebook que vous écrivez, puis un proposeur | Un tagueur automatique |
| Un walk humain, puis des packets que vous rouvrez | Une application qui fait l'open coding à votre place |

<h2 id="rights">Droits</h2>

Les transcriptions restent sur la machine qui les a récupérées. Il faut le droit de les conserver. Ne commitez pas les mots des autres. Ce dépôt livre une fixture synthétique et un domain pack vide. Vos sources, cartes et tags sont à vous, dans votre copie de travail privée.

<h2 id="setup">Installation</h2>

<h3 id="setup-video">Vidéo</h3>

`yt-dlp` et `youtube-transcript-api`, déjà dans le démarrage, suffisent pour les sous-titres. Si YouTube demande une connexion, ajoutez `--cookies-from-browser chrome` à `cited.py add`. Si une récupération casse après un changement du site, mettez `yt-dlp` à jour.

<h3 id="setup-podcasts">Podcasts</h3>

Un flux qui embarque une transcription est utilisé tel quel. Sinon l'audio est transcrit localement. Rien n'est envoyé.

```bash
# Apple Silicon
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# partout ailleurs
python3 -m pip install -U faster-whisper
```

La première transcription télécharge un modèle Whisper (environ 1,5 Go). L'indice de vocabulaire se règle dans `domain/whisper_prompt.txt`. L'exemple est générique. Remplacez-le par les noms propres de votre domaine, sinon ils seront mal entendus.

<h3 id="setup-tagging">Tags</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# télécharger BAAI/bge-small-en-v1.5 dans models/bge-small
# (MIT). Les poids ne sont pas dans ce dépôt.
```

`cited.py mine propose` utilise ce modèle local. Sans lui, la recherche, les cartes et les briefs marchent encore. On tague à la main, ou on installe le modèle.

<h3 id="setup-domain">Votre domain pack</h3>

```bash
cp -R domain.example domain
```

Quatre fichiers à éditer avant de taguer à une vraie échelle :

- `domain/categories.json` — id, name, definition, aliases. Les deux exemples sont des placeholders.
- `domain/card.json` — les topics et les vocabulaires fermés d'une carte.
- `domain/layer1.md` — un paragraphe : ce que vous tenez pour cette question en ce moment, et ce que vous ne tenez pas.
- `domain/whisper_prompt.txt` — les noms et les termes que le transcripteur doit attendre.

<h2 id="first-hour">La première heure</h2>

1. Lancer le démarrage et vérifier que la fixture se cherche.
2. Récupérer une source que vous avez le droit de garder. Lister avant de télécharger.

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests`, puis `python3 cited.py meta <id> --guest "…" --role "…" --company "…"` jusqu'à ce que les points d'interrogation disparaissent.
4. S'arrêter. Écrire la carte. Pas encore de `propose`.

<h2 id="human-work">Le travail humain</h2>

Les commandes tournent très bien sur une théorie vide et une pile d'épisodes où vous ne reviendrez pas. Ces étapes font de la base quelque chose dont vous apprenez. Chacune a un état fini. La sauter produit un échec précis.

<details>
<summary><b>1 · Lentille</b> — écrire la question avant de télécharger</summary>

<br>

Écrivez la question, puis les règles de ce qui peut entrer : cela porte sur la question, les récaps et les best-of restent dehors, le même invité apparaît au plus deux fois, les voix qui contestent restent.

C'est fini quand quelqu'un d'autre pourrait appliquer les règles à un nouvel épisode.

Sans cela, le corpus est tout ce que le flux a publié.

</details>

<details>
<summary><b>2 · Ingestion</b> — lister, puis récupérer, et taguer l'émission</summary>

<br>

`pod --list` ou `queue` d'abord. Taguer l'émission à l'entrée.

C'est fini quand chaque fichier de `transcripts/` est un fichier que vous comptez mettre en carte.

Sans cela, vous transcrivez des heures que vous n'encoderez jamais.

</details>

<details>
<summary><b>3 · Noms</b> — la reconnaissance vocale se trompe sur les gens et les chiffres</summary>

<br>

`cited.py guests`, puis `cited.py meta` pour chaque `?`. Vérifiez les noms et les nombres contre les notes d'émission.

C'est fini quand une citation nommerait la bonne personne.

Sans cela, vous créditez la mauvaise.

</details>

<details>
<summary><b>4 · Cartes minces</b> — la carte est la preuve, la transcription est le contrôle</summary>

<br>

Un agent peut rédiger depuis `cited.py card-scaffold`. Vous lancez `validate_cards.py`. Paraphraser. Chaque horodatage doit être le début d'un paragraphe dans la transcription. Deux citations au plus, courtes et verbatim.

C'est fini quand le validateur se tait et que `reindex` montre les nouveaux claims.

Sans cela, l'index est une fiction.

</details>

<details>
<summary><b>5 · Codebook</b> — l'écrire depuis vos sources, puis allumer propose</summary>

<br>

Lisez une quinzaine de sources. Écrivez les catégories avec vos mots : id, name, definition, aliases. Taguez un échantillon à la main. Un passage complet d'open coding est un autre projet, et un projet cher. Les placeholders de `domain.example` ne sont pas une théorie.

C'est fini quand vous pouvez expliquer chaque catégorie sans regarder un score.

Sans cela, vous taguez le corpus avec les exemples, ou avec la question de quelqu'un d'autre.

</details>

<details>
<summary><b>6 · Calibrer</b> — les catégories floues quittent la file par défaut</summary>

<br>

Marquez chaque catégorie clear, fuzzy ou unclear dans `domain/calibration.jsonl`. Unclear reste hors de `mine walk` sauf si vous passez `--include-unclear`.

C'est fini quand la file ne contient que des catégories que vous savez appliquer.

Sans cela, le temps de revue s'enfonce dans celles que vous ne savez pas appliquer.

</details>

<details>
<summary><b>7 · Walk</b> — accepter est une touche humaine</summary>

<br>

<kbd>a</kbd> accept, <kbd>r</kbd> reject, <kbd>n</kbd> none, <kbd>s</kbd> skip, <kbd>q</kbd> quit. Un doute veut dire skip. Reject seulement quand vous comprenez à la fois le claim et la catégorie. Pas d'accept en masse.

C'est fini quand chaque ligne acceptée est une ligne que vous diriez à voix haute.

Sans cela, les comptes sont l'opinion du modèle.

</details>

<details>
<summary><b>8 · Divulgation</b> — un vendeur ne devient pas un témoin indépendant</summary>

<br>

Si l'invité vend ce dont on parle, ou si l'épisode est sponsorisé, ce drapeau reste sur chaque citation qui porte un résultat.

C'est fini quand un épisode de vendeur ne peut pas se lire comme une pratique indépendante.

Sans cela, une conversation commerciale devient une preuve.

</details>

<details>
<summary><b>9 · Packets</b> — un packet par question que vous apprenez</summary>

<br>

Rafraîchissez les packets à partir des tags acceptés seulement. Le packet anomaly est le bassin des `none`. C'est là que vous regardez quand un claim n'a pas tenu. Ce n'est pas un thème à part.

C'est fini quand `cited.py packet list` correspond aux questions que vous étudiez vraiment.

Sans cela, chaque fois que vous voulez vous souvenir, vous repartez d'une recherche.

</details>

<details>
<summary><b>10 · Étude</b> — revenir à la question, pas au dossier</summary>

<br>

`cited.py brief` rassemble les claims acceptés pour une question. C'est la passe d'étude. La recherche sert quand ce packet est mince. Le dossier des transcriptions n'est pas le contexte.

C'est fini quand vous pouvez redire la question depuis le brief sans ouvrir un épisode.

Sans cela, vous réécoutez, ou vous faites confiance à un souvenir vague.

</details>

<details>
<summary><b>11 · Trois couches</b> — séparer ce qu'ils ont dit de ce que vous pensez maintenant</summary>

<br>

Quand vous vous expliquez une question, gardez trois couches séparées : les catégories que vous avez figées, l'ensemble plus large d'épisodes, et votre propre conclusion. La troisième est votre apprentissage. Ce n'est pas quelque chose que les invités ont prouvé.

C'est fini quand vous pouvez montrer quelle part est la vôtre.

Sans cela, une conclusion durcit en « les podcasts l'ont dit ».

</details>

<details>
<summary><b>12 · Dénominateurs</b> — savoir ce que vous avez vraiment pris</summary>

<br>

`cited.py corpus` imprime combien d'épisodes vous avez récupérés, combien vous avez mis en carte, et combien de claims vous avez acceptés. Ce sont des comptes différents.

C'est fini quand vous pouvez dire quel compte vous visez.

Sans cela, un dossier de téléchargements a le goût de la maîtrise.

</details>

<details>
<summary><b>13 · Dérive</b> — une catégorie nouvelle est une décision écrite</summary>

<br>

À intervalle fixe, lisez le taux de none, le packet anomaly, et les Gaps des cartes. Décidez : tenir, clarifier une définition, ou étendre avec une catégorie provisoire. Écrivez la décision. Rouvrir l'open coding est un choix à part, pas une suggestion de l'outil parce qu'un épisode était étrange.

C'est fini quand le codebook a une note datée, y compris quand la note est « hold ».

Sans cela, un épisode étrange devient une catégorie.

</details>

<h2 id="recall">Revenir</h2>

Quand un point compte, revenez à la minute. `cited.py show <id> --at mm:ss --window 1`. Une citation reste sous quinze mots. Nommez la personne, l'organisation et l'émission. La carte est une paraphrase. L'horodatage est le chemin du retour.

<h2 id="later">Ensuite</h2>

La base est pour votre propre apprentissage. Une fois qu'une question tient, les mêmes packets servent pour une note, une intervention, une passation ou un cours. Ces usages sont réunis dans [`LATER.md`](LATER.md) (en anglais).

<h2 id="layout">Agencement</h2>

```text
cited.py           la commande
domain.py          charge ton pack de domaine
validate_cards.py  les cartes contre le domain pack et la transcription
kbbert.py          plongements locaux, sans torch
mining/            propose, walk, packets, brief
domain.example/    à copier vers domain/ puis à éditer
domain/            vos catégories, le schéma de carte, la layer-1, le prompt
examples/fixture/  transcription synthétique et une carte
transcripts/       à vous, pas pour ce dépôt public
cards/             à vous
AGENT.md           ce qu'un agent peut faire
LATER.md           des idées, une fois qu'une question tient
```

Dans une copie de travail, `transcripts/`, `cards/`, `cited.sqlite` et `models/` sont gitignorés. `reindex` reconstruit l'index depuis les fichiers.

<h2 id="languages">Langues</h2>

La barre du haut est le changement de langue. La langue que vous lisez est du texte simple. Les autres sont des liens. L'anglais est le texte source.

Une traduction est un fichier voisin : `README.de.md`, `README.zh-CN.md`, `README.ja.md`, `README.ko.md`, `README.fr.md`, `README.es.md`. On traduit la prose et les titres. On ne traduit pas les commandes, les flags, les noms de fichiers, les id de catégorie, ni les touches <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd>. Les id de titre sont les mêmes dans chaque fichier, donc `#quick-start` survit au changement de langue.

Pour ajouter une langue, copiez `README.md`, traduisez la prose, et marquez cette langue avec `<strong>` dans sa propre barre.

<h2 id="license">Licence</h2>

Le code est sous [MIT](LICENSE). Les poids BGE et les modèles Whisper sont des téléchargements séparés, avec leurs licences. Les transcriptions que vous récupérez ne sont pas relicenciées par ce projet.

<p align="center">
  <strong>English</strong> ·
  <a href="README.de.md">Deutsch</a> ·
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

<p>Podcasts and talks in. A knowledge base you learn from.</p>

<p>Embeddings propose. A person accepts.</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="Transcripts stay on your machine" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">Quick start</a> ·
  <a href="#the-loop">The loop</a> ·
  <a href="#human-work">Human work</a> ·
  <a href="#recall">Recall</a> ·
  <a href="#later">Later</a> ·
  <a href="#layout">Layout</a>
</p>
</div>

---

<h2 id="quick-start">Quick start</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

Python 3.9 or newer, with SQLite FTS5 (the usual macOS and python.org builds). The fixture is synthetic, so this runs before you fetch anything. Whisper and the tagger are optional. Setup for both is below.

<h2 id="the-loop">The loop</h2>

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

`propose` writes candidates. `walk` is where a tag becomes part of what you know. Only accepted tags enter a packet. `brief` is how you sit back down with one question, without replaying the episodes.

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

An agent may draft cards and may pull a question back up from a brief. It may not accept a tag, invent a category, or read a whole transcript in order to summarize what you learned. The short version of that contract is [`AGENT.md`](AGENT.md).

<h2 id="what-this-is">What this is</h2>

| This is | This is not |
|---|---|
| A local knowledge base you learn from: podcasts and talks become claims you can return to | A hosted corpus, or someone else's finished course |
| Thin cards and an index, so you stop re-reading the recording | A summary machine |
| A codebook you write, then a proposer | An auto-tagger |
| A human walk, then packets you can revisit | An app that does open coding for you |

<h2 id="rights">Rights</h2>

Transcripts stay on the machine that fetched them. You need the right to keep them. Do not commit other people's words. This repository ships a synthetic fixture and an empty domain pack. Your sources, cards, and tags are yours, and they belong in your own private working copy.

<h2 id="setup">Setup</h2>

<h3 id="setup-video">Video</h3>

`yt-dlp` and `youtube-transcript-api` from the quick start are enough for captions. If YouTube asks you to sign in, add `--cookies-from-browser chrome` on `cited.py add`. If a fetch breaks after a site change, upgrade `yt-dlp`.

<h3 id="setup-podcasts">Podcasts</h3>

Feeds that ship a transcript are used as-is. Otherwise the audio is transcribed locally. Nothing is uploaded.

```bash
# Apple Silicon
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# anywhere else
python3 -m pip install -U faster-whisper
```

The first transcription downloads a Whisper model (about 1.5 GB). Set the vocabulary hint in `domain/whisper_prompt.txt`. The sample prompt is generic. Replace it with the proper names in your field, or those names will be mis-heard.

<h3 id="setup-tagging">Tagging</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# download BAAI/bge-small-en-v1.5 into models/bge-small
# (MIT). The weights are not in this repo.
```

`cited.py mine propose` uses that local model. Without it, search, cards, and briefs still work. You tag by hand, or you install the model.

<h3 id="setup-domain">Your domain pack</h3>

```bash
cp -R domain.example domain
```

Edit four things before you tag at any scale:

- `domain/categories.json` — id, name, definition, aliases. The two samples are placeholders.
- `domain/card.json` — topics and the closed vocabularies on a card.
- `domain/layer1.md` — one paragraph: what you currently hold on this question, and what you do not.
- `domain/whisper_prompt.txt` — names and terms the transcriber should expect.

<h2 id="first-hour">The first hour</h2>

1. Run the quick start and confirm the fixture searches.
2. Fetch one source you have rights to. List before you download.

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests`, then `python3 cited.py meta <id> --guest "…" --role "…" --company "…"` until the question marks are gone.
4. Stop. Write the card. Do not propose yet.

<h2 id="human-work">Human work</h2>

The commands run fine on an empty theory and a pile of episodes you will never revisit. These steps are what make the base something you can learn from. Each one has a finished state. Skip it and the failure is specific.

<details>
<summary><b>1 · Lens</b> — write the question before you download</summary>

<br>

Write the question, then the rules for what may enter: it bears on the question, recaps and best-ofs stay out, the same guest appears at most twice, voices that disagree stay in.

Done when someone else could apply the rules to a new episode.

Without this, the corpus is whatever the feed published.

</details>

<details>
<summary><b>2 · Ingest</b> — list, then fetch, and tag the show</summary>

<br>

`pod --list` or `queue` first. Tag the show on the way in.

Done when every file in `transcripts/` is one you intend to card.

Without this, you transcribe hours you will never encode.

</details>

<details>
<summary><b>3 · Names</b> — speech-to-text lies about people and figures</summary>

<br>

`cited.py guests`, then `cited.py meta` for every `?`. Check names and numbers against the show notes.

Done when a cite would name the right person.

Without this, you credit the wrong one.

</details>

<details>
<summary><b>4 · Thin cards</b> — the card is the evidence, the transcript is the check</summary>

<br>

An agent may draft from `cited.py card-scaffold`. You run `validate_cards.py`. Paraphrase. Every timestamp has to be a paragraph start in the transcript. Two quotes at most, each short and verbatim.

Done when the validator is quiet and `reindex` shows the new claims.

Without this, the index is fiction.

</details>

<details>
<summary><b>5 · Codebook</b> — write it from your sources, then turn propose on</summary>

<br>

Read about fifteen sources. Write categories in your own words: id, name, definition, aliases. Hand-tag a sample. A full open-coding pass is a separate project, and an expensive one. The placeholders in `domain.example` are not a theory.

Done when you can explain each category without looking at a score.

Without this, you tag the corpus with the samples, or with someone else's question.

</details>

<details>
<summary><b>6 · Calibrate</b> — unclear categories leave the default queue</summary>

<br>

Mark each category clear, fuzzy, or unclear in `domain/calibration.jsonl`. Unclear stays out of `mine walk` unless you pass `--include-unclear`.

Done when the queue is only categories you can apply.

Without this, review time sinks into ones you cannot.

</details>

<details>
<summary><b>7 · Walk</b> — accept is a human key</summary>

<br>

<kbd>a</kbd> accept, <kbd>r</kbd> reject, <kbd>n</kbd> none, <kbd>s</kbd> skip, <kbd>q</kbd> quit. Unsure means skip. Reject only when you understand both the claim and the category. There is no bulk accept.

Done when every accepted row is one you would say out loud.

Without this, the counts are the model's opinion.

</details>

<details>
<summary><b>8 · Disclosure</b> — a seller does not become an independent witness</summary>

<br>

If the guest sells the thing under discussion, or the episode is sponsored, that flag stays on every cite that carries a finding.

Done when a vendor episode cannot be read as independent practice.

Without this, a sales conversation becomes evidence.

</details>

<details>
<summary><b>9 · Packets</b> — one packet per question you are learning</summary>

<br>

Refresh packets from accepted tags only. The anomaly packet is the pool of `none`. It is where you look when a claim did not fit, not a theme of its own.

Done when `cited.py packet list` matches the questions you are actually studying.

Without this, every time you want to remember, you start from a fresh search.

</details>

<details>
<summary><b>10 · Study</b> — revisit the question, not the folder</summary>

<br>

`cited.py brief` gathers the accepted claims for one question. That is the study pass. Search only when that packet is thin. The transcript folder is not the context.

Done when you can restate the question from the brief without opening an episode.

Without this, you re-listen, or you trust a vague memory.

</details>

<details>
<summary><b>11 · Three layers</b> — separate what they said from what you now think</summary>

<br>

When you explain a question to yourself, keep three layers apart: the categories you have frozen, the wider set of episodes, and your own conclusion. The third is your learning. It is not something the guests proved.

Done when you can point at which part is yours.

Without this, a conclusion hardens into "the podcasts said so."

</details>

<details>
<summary><b>12 · Denominators</b> — know what you have actually taken in</summary>

<br>

`cited.py corpus` prints how many episodes you fetched, how many you carded, and how many claims you accepted. Those are different counts.

Done when you can say which count you mean.

Without this, a download folder feels like mastery.

</details>

<details>
<summary><b>13 · Drift</b> — a new category is a written decision</summary>

<br>

On a schedule, read the none-rate, the anomaly packet, and the Gaps on the cards. Decide hold, clarify a definition, or extend with a provisional category. Write the decision down. Reopening open coding is its own choice, not a suggestion the tool makes because one episode was odd.

Done when the codebook has a dated note, including when the note is "hold".

Without this, one strange episode becomes a new category.

</details>

<h2 id="recall">Recall</h2>

When a point matters, go back to the minute. `cited.py show <id> --at mm:ss --window 1`. A quote stays under fifteen words. Name the speaker, the organisation, and the show. The card is a paraphrase. The timestamp is how you return.

<h2 id="later">Later</h2>

The base is for your own learning. Once a question is solid, the same packets are ready for a note, a talk, a handoff, or a class. Those uses are gathered in [`LATER.md`](LATER.md).

<h2 id="layout">Layout</h2>

```text
cited.py           the command
domain.py          loads your domain pack
validate_cards.py  cards against the domain pack and the transcript
kbbert.py          local embeddings, no torch
mining/            propose, walk, packets, brief
domain.example/    copy to domain/ and edit
domain/            your categories, card schema, layer-1, prompt
examples/fixture/  synthetic transcript and card
transcripts/       yours, not for this public repo
cards/             yours
AGENT.md           what an agent may do
LATER.md           ideas for once a question is solid
```

`transcripts/`, `cards/`, `cited.sqlite`, and `models/` are gitignored in a working copy. `reindex` rebuilds the index from the files.

<h2 id="languages">Languages</h2>

The bar at the top is the locale switch. The language you are reading is plain text. The others are links. English is the source text.

A translation is a sibling file: `README.de.md`, `README.zh-CN.md`, `README.ja.md`, `README.ko.md`, `README.fr.md`, `README.es.md`. Prose and headings are translated. Commands, flags, file names, category ids, and the keys <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd> are not. Heading ids are the same in every file, so `#quick-start` survives a language change.

To add a language, copy `README.md`, translate the prose, and mark that language with `<strong>` in its own bar.

<h2 id="license">License</h2>

Code is [MIT](LICENSE). The BGE weights and the Whisper models are separate downloads with their own licenses. Transcripts you fetch are not relicensed by this project.

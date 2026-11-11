<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <strong>日本語</strong> ·
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

<p>ポッドキャストとトークを入れる。自分の学びに使う知識ベースになる。</p>

<p>埋め込みは提案する。受け入れるのは人。</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="MIT ライセンス" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="文字起こしは手元に残す" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">クイックスタート</a> ·
  <a href="#the-loop">流れ</a> ·
  <a href="#human-work">人がやること</a> ·
  <a href="#recall">戻る</a> ·
  <a href="#later">その後</a> ·
  <a href="#layout">構成</a>
</p>
</div>

---

<h2 id="quick-start">クイックスタート</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

Python 3.9 以降と SQLite FTS5（macOS と python.org の通常ビルドに含まれる）。フィクスチャは合成データなので、何も取得する前に動く。Whisper とタガーは任意。両方の準備は下にある。

<h2 id="the-loop">流れ</h2>

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

`propose` は候補を書く。`walk` でタグは自分の知っていることの一部になる。packet に入るのは受け入れたタグだけ。`brief` は、回を聞き直さずに一つの問いへ戻るやり方である。

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

エージェントはカードを下書きし、brief から問いを呼び戻せる。タグの受け入れ、カテゴリの新設、学んだことの要約のための文字起こし全文の読解はしない。短い契約は [`AGENT.md`](AGENT.md)（英語。規則は同じ）。

<h2 id="what-this-is">これは何か</h2>

| これである | これではない |
|---|---|
| 自分で学ぶための手元の知識ベース。ポッドキャストとトークが、戻れる claim になる | ホストされたコーパスや、誰かの完成した講座 |
| 薄いカードと索引。録音を聞き直さずに済む | 要約マシン |
| 自分で書く codebook と、その後の提案器 | 自動タガー |
| 人の walk と、あとから開く packet | オープンコーディングを代行するアプリ |

<h2 id="rights">権利</h2>

文字起こしは取得したマシンに残す。保持する権利が要る。他人の言葉をコミットしない。このリポジトリが含むのは合成フィクスチャと空のドメインパックだけ。素材、カード、タグは自分のもので、非公開の作業コピーに置く。

<h2 id="setup">セットアップ</h2>

<h3 id="setup-video">動画</h3>

クイックスタートの `yt-dlp` と `youtube-transcript-api` で字幕は取れる。YouTube がログインを求めたら、`cited.py add` に `--cookies-from-browser chrome` を付ける。サイト変更で取得が壊れたら `yt-dlp` を上げる。

<h3 id="setup-podcasts">ポッドキャスト</h3>

フィードに文字起こしがあればそれを使う。なければ音声をローカルで書き起こす。アップロードはしない。

```bash
# Apple Silicon
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# それ以外
python3 -m pip install -U faster-whisper
```

最初の書き起こしで Whisper のモデルを取得する（約 1.5 GB）。語彙のヒントは `domain/whisper_prompt.txt`。サンプルは汎用なので、分野の固有名詞に替える。替えないと名前を聞き間違える。

<h3 id="setup-tagging">タグ付け</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# BAAI/bge-small-en-v1.5 を models/bge-small に置く
# （MIT）。重みはこのリポジトリにない。
```

`cited.py mine propose` はこのローカルモデルを使う。無くても検索、カード、brief は動く。手でタグを付けるか、モデルを入れる。

<h3 id="setup-domain">ドメインパック</h3>

```bash
cp -R domain.example domain
```

規模のあるタグ付けの前に、四つを編集する。

- `domain/categories.json` — id、name、definition、aliases。二つはプレースホルダ。
- `domain/card.json` — トピックと、カードの閉じた語彙。
- `domain/layer1.md` — 一段落。この問いについて今持っていることと、持っていないこと。
- `domain/whisper_prompt.txt` — 書き起こし側が期待すべき名前と用語。

<h2 id="first-hour">最初の 1 時間</h2>

1. クイックスタートを実行し、フィクスチャが検索できることを確認する。
2. 保持する権利のある素材を一つ取る。取得の前に一覧する。

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests` のあと、`?` が無くなるまで `python3 cited.py meta <id> --guest "…" --role "…" --company "…"`。
4. ここで止める。カードを書く。まだ `propose` しない。

<h2 id="human-work">人がやること</h2>

コマンドは、空の理論と、二度と戻らない回の山でも動く。次の手順が、学べるベースにする。それぞれに完了の形がある。飛ばすと、失敗の仕方は決まっている。

<details>
<summary><b>1 · レンズ</b> — 取得する前に問いを書く</summary>

<br>

問いを書き、入れてよいものの規則を書く。問いに関係すること。総集編とベスト盤は入れない。同じゲストは多くて二回。反対する声は残す。

完了は、別の人がその規則を新しい回に適用できるとき。

これがないと、コーパスはフィードが配ったもの全部になる。

</details>

<details>
<summary><b>2 · 取り込み</b> — 一覧してから取り、番組にタグを付ける</summary>

<br>

先に `pod --list` か `queue`。取り込み時に番組へタグを付ける。

完了は、`transcripts/` の各ファイルがカードにするつもりのものであるとき。

これがないと、符号化しない時間を書き起こす。

</details>

<details>
<summary><b>3 · 名前</b> — 音声認識は人と数字を間違える</summary>

<br>

`cited.py guests`、それから各 `?` に `cited.py meta`。名前と数字をショーノートと照合する。

完了は、引用が正しい人を名指しできるとき。

これがないと、別人の功績になる。

</details>

<details>
<summary><b>4 · 薄いカード</b> — カードが証拠、文字起こしは確認</summary>

<br>

エージェントは `cited.py card-scaffold` から下書きしてよい。検証は `validate_cards.py`。言い換える。タイムスタンプは文字起こしの段落の先頭である必要がある。引用は多くて二つ、短く、一字一句。

完了は、バリデータが黙り、`reindex` が新しい claim を見せるとき。

これがないと、索引は作り物である。

</details>

<details>
<summary><b>5 · Codebook</b> — 自分の素材から書き、その後で propose を付ける</summary>

<br>

十五本ほど読む。カテゴリは自分の言葉で書く。id、name、definition、aliases。サンプルは手でタグ付けする。オープンコーディングの全工程は別の仕事で、高い。`domain.example` のプレースホルダは理論ではない。

完了は、スコアを見ずに各カテゴリを説明できるとき。

これがないと、サンプルか、他人の問いでコーパスをタグ付けすることになる。

</details>

<details>
<summary><b>6 · 較正</b> — 不明なカテゴリは既定の列から外す</summary>

<br>

`domain/calibration.jsonl` で各カテゴリを clear、fuzzy、unclear にする。unclear は `--include-unclear` を付けない限り `mine walk` に出ない。

完了は、列にあるのが適用できるカテゴリだけのとき。

これがないと、適用できないものにレビューの時間が沈む。

</details>

<details>
<summary><b>7 · Walk</b> — 受け入れは人が押すキー</summary>

<br>

<kbd>a</kbd> accept、<kbd>r</kbd> reject、<kbd>n</kbd> none、<kbd>s</kbd> skip、<kbd>q</kbd> quit。迷ったら skip。reject は claim とカテゴリの両方を理解しているときだけ。一括の accept はない。

完了は、受け入れた各行を声に出して言えるとき。

これがないと、件数はモデルの意見である。

</details>

<details>
<summary><b>8 · 開示</b> — 売り手は独立した証人にならない</summary>

<br>

ゲストが話題のものを売っている、または回がスポンサードなら、その旗は発見を運ぶ引用のすべてに残す。

完了は、ベンダーの回を独立した実践として読めないとき。

これがないと、販売の会話が証拠になる。

</details>

<details>
<summary><b>9 · Packet</b> — 学んでいる問いにつき一つ</summary>

<br>

packet は受け入れたタグだけから更新する。anomaly packet は `none` の溜まりである。claim が合わなかったときに見る場所であり、独立したテーマではない。

完了は、`cited.py packet list` が今学んでいる問いに一致するとき。

これがないと、思い出したいたびに新しい検索から始める。

</details>

<details>
<summary><b>10 · 学習</b> — 問いに戻る。フォルダには戻らない</summary>

<br>

`cited.py brief` は一つの問いについて受け入れた claim を集める。それが学習の一回である。検索はその packet が薄いときだけ。文字起こしのフォルダは文脈ではない。

完了は、回を開かずに brief から問いを言い直せるとき。

これがないと、聞き直すか、曖昧な記憶を信じることになる。

</details>

<details>
<summary><b>11 · 三つの層</b> — 言われたことと、今思うことを分ける</summary>

<br>

問いを自分に説明するときは三層を分ける。凍ったカテゴリ、より広い回の集まり、自分の結論。三層目は自分の学びである。ゲストが証明したことではない。

完了は、どの部分が自分のものか指させるとき。

これがないと、結論が「ポッドキャストがそう言った」に固まる。

</details>

<details>
<summary><b>12 · 分母</b> — 実際に取り込んだ量を知る</summary>

<br>

`cited.py corpus` は、取得した本数、カードにした本数、受け入れた claim の数を出す。これらは別の数である。

完了は、どの数を指しているか言えるとき。

これがないと、ダウンロードしたフォルダが習得に感じられる。

</details>

<details>
<summary><b>13 · ドリフト</b> — 新しいカテゴリは書いた決定である</summary>

<br>

周期的に、none の割合、anomaly packet、カードの Gaps を読む。hold するか、定義を明確にするか、暫定カテゴリで広げるかを決める。決定を書く。オープンコーディングを再開するのは別の選択であり、一本が奇妙だったからツールが勧めることではない。

完了は、codebook に日付付きのメモがあるとき。メモが「hold」でもよい。

これがないと、奇妙な一本が新しいカテゴリになる。

</details>

<h2 id="recall">戻る</h2>

点が重要なら、その分へ戻る。`cited.py show <id> --at mm:ss --window 1`。引用は十五語以内。話者、組織、番組を記す。カードは言い換えである。タイムスタンプが戻り方である。

<h2 id="later">その後</h2>

このベースは自分の学びのためにある。問いが固まったら、同じ packet がメモ、話、引き継ぎ、授業に使える。それらの使い方は [`LATER.md`](LATER.md)（英語）にまとめてある。

<h2 id="layout">構成</h2>

```text
cited.py           コマンド
domain.py          ドメインパックを読む
validate_cards.py  ドメインパックと文字起こしに対するカード検証
kbbert.py          ローカル埋め込み。torch は不要
mining/            propose、walk、packets、brief
domain.example/    domain/ にコピーして編集
domain/            カテゴリ、カードのスキーマ、layer-1、プロンプト
examples/fixture/  合成の文字起こしとカード
transcripts/       自分のもの。この公開リポジトリには入れない
cards/             自分のもの
AGENT.md           エージェントがしてよいこと
LATER.md           問いが固まってからできること
```

作業コピーでは `transcripts/`、`cards/`、`cited.sqlite`、`models/` は gitignore される。`reindex` はファイルから索引を作り直す。

<h2 id="languages">言語</h2>

ページ上部のバーが言語の切り替えである。読んでいる言語はプレーンテキスト、他はリンク。英語が原文。

翻訳は兄弟ファイルである。`README.de.md`、`README.zh-CN.md`、`README.ja.md`、`README.ko.md`、`README.fr.md`、`README.es.md`。訳すのは散文と見出し。コマンド、フラグ、ファイル名、カテゴリ id、キー <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd> は訳さない。見出し id は全ファイルで同じなので、言語を替えても `#quick-start` は有効。

言語を足すには `README.md` をコピーし、散文を訳し、そのファイルのバーでその言語を `<strong>` にする。

<h2 id="license">ライセンス</h2>

コードは [MIT](LICENSE)。BGE の重みと Whisper のモデルは別ダウンロードで、ライセンスも別。取得した文字起こしがこのプロジェクトによって再許諾されることはない。

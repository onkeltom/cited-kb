<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <strong>简体中文</strong> ·
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

<p>播客和演讲进来。一座供你自己学习的知识库。</p>

<p>嵌入只负责提议。接受的是人。</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="MIT 许可证" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="转写留在你的机器上" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">快速开始</a> ·
  <a href="#the-loop">流程</a> ·
  <a href="#human-work">人要做的事</a> ·
  <a href="#recall">回顾</a> ·
  <a href="#later">以后</a> ·
  <a href="#layout">目录</a>
</p>
</div>

---

<h2 id="quick-start">快速开始</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

需要 Python 3.9 或更新版本，以及 SQLite FTS5（macOS 和 python.org 的常见构建已包含）。示例是合成的，所以在抓取任何内容之前就能跑通。Whisper 和打标是可选的，安装见下文。

<h2 id="the-loop">流程</h2>

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

`propose` 写出候选。`walk` 是一条标签变成你所知的地方。只有被接受的标签会进入 packet。`brief` 是你重新坐下来面对一个问题的方式，不必把各集再听一遍。

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

代理可以起草卡片，也可以用 brief 把一个问题重新调出来。它不能接受标签、发明类别，也不能为了概括你学到了什么而通读整份转写。[`AGENT.md`](AGENT.md) 是这份约定的短版（英文，规则相同）。

<h2 id="what-this-is">这是什么</h2>

| 是 | 不是 |
|---|---|
| 一座供你学习的本地知识库：播客和演讲变成你可以返回的 claim | 一个托管语料库，或别人已经做好的课程 |
| 薄卡片加索引，这样你不必把录音再听一遍 | 一台摘要机器 |
| 你自己写的 codebook，然后才是提议器 | 一个自动打标器 |
| 人工 walk，然后是你可以再次打开的 packet | 一个替你做开放编码的应用 |

<h2 id="rights">权利</h2>

转写留在抓取它的那台机器上。你需要有保留它们的权利。不要提交别人的原话。本仓库只带一份合成示例和一个空的领域包。你的材料、卡片和标签属于你，放在你自己的私有工作副本里。

<h2 id="setup">安装</h2>

<h3 id="setup-video">视频</h3>

快速开始里的 `yt-dlp` 和 `youtube-transcript-api` 足够拉取字幕。如果 YouTube 要求登录，在 `cited.py add` 上加 `--cookies-from-browser chrome`。站点改版后抓取失败，就升级 `yt-dlp`。

<h3 id="setup-podcasts">播客</h3>

源里自带转写就直接用。否则在本地转写音频。不会上传。

```bash
# Apple 芯片
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# 其他环境
python3 -m pip install -U faster-whisper
```

第一次转写会下载 Whisper 模型（约 1.5 GB）。词表提示写在 `domain/whisper_prompt.txt`。示例提示是通用的。换成你这个领域的专名，否则这些名字会被听错。

<h3 id="setup-tagging">打标</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# 把 BAAI/bge-small-en-v1.5 下载到 models/bge-small
# （MIT）。权重不在本仓库里。
```

`cited.py mine propose` 使用这个本地模型。没有它，搜索、卡片和 brief 仍然可用。你可以手打标签，或者装上模型。

<h3 id="setup-domain">你的领域包</h3>

```bash
cp -R domain.example domain
```

大规模打标之前先改这四处：

- `domain/categories.json` — id、name、definition、aliases。那两条是占位。
- `domain/card.json` — 主题，以及卡片上的封闭词表。
- `domain/layer1.md` — 一段话：你目前对这个问题持有什么，不持有什么。
- `domain/whisper_prompt.txt` — 转写器应该预期的人名和术语。

<h2 id="first-hour">第一个小时</h2>

1. 跑通快速开始，确认示例能被搜到。
2. 抓一份你有权保留的材料。先列出，再下载。

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests`，然后对每个 `?` 运行 `python3 cited.py meta <id> --guest "…" --role "…" --company "…"`，直到问号消失。
4. 停。写卡片。先不要 `propose`。

<h2 id="human-work">人要做的事</h2>

这些命令在一套空理论和一堆你不会再回去听的节目上也能跑。下面的步骤让这个库成为你可以学习的东西。每一步都有完成的样子。跳过它，失败是具体的。

<details>
<summary><b>1 · 镜头</b> — 下载之前先写下问题</summary>

<br>

先写问题，再写准入规则：要和问题有关，回顾和精选集不收，同一位嘉宾最多出现两次，不同意的声音留下来。

完成的样子：另一个人能把这些规则用到新的一集上。

没有这一步，语料就是订阅源发布的一切。

</details>

<details>
<summary><b>2 · 入库</b> — 先列出，再抓取，并给节目打上标签</summary>

<br>

先 `pod --list` 或 `queue`。入库时给节目打标签。

完成的样子：`transcripts/` 里的每一份文件都是你打算做卡片的。

没有这一步，你会转写很多永远不会编码的小时。

</details>

<details>
<summary><b>3 · 名字</b> — 语音识别会把人和数字听错</summary>

<br>

`cited.py guests`，然后对每个 `?` 用 `cited.py meta`。对照节目备注核对姓名和数字。

完成的样子：一条引用会指向正确的人。

没有这一步，你会把功劳记到别人头上。

</details>

<details>
<summary><b>4 · 薄卡片</b> — 卡片是证据，转写是核对</summary>

<br>

代理可以从 `cited.py card-scaffold` 起草。你来跑 `validate_cards.py`。用转述。每个时间戳都必须是转写里某一段的开头。引用最多两处，短，且逐字。

完成的样子：校验器没有输出，`reindex` 能看到新的 claim。

没有这一步，索引是虚构的。

</details>

<details>
<summary><b>5 · Codebook</b> — 从你的材料里写出来，再打开 propose</summary>

<br>

读大约十五份材料。用你自己的话写类别：id、name、definition、aliases。先手打一个小样本。完整的开放编码是另一项工作，而且很贵。`domain.example` 里的占位不是一套理论。

完成的样子：你不看分数也能解释每一个类别。

没有这一步，你是在用占位符，或用别人的问题，给语料打标。

</details>

<details>
<summary><b>6 · 校准</b> — 不清楚的类别离开默认队列</summary>

<br>

在 `domain/calibration.jsonl` 里把每个类别标成 clear、fuzzy 或 unclear。unclear 不会进入 `mine walk`，除非你加上 `--include-unclear`。

完成的样子：队列里只剩你用得上的类别。

没有这一步，审阅时间会耗在你无法判断的类别上。

</details>

<details>
<summary><b>7 · Walk</b> — 接受是人按的键</summary>

<br>

<kbd>a</kbd> accept，<kbd>r</kbd> reject，<kbd>n</kbd> none，<kbd>s</kbd> skip，<kbd>q</kbd> quit。拿不准就 skip。只有当你同时理解这条 claim 和这个类别时才 reject。没有批量接受。

完成的样子：每一条被接受的记录，你都愿意说出口。

没有这一步，那些数字是模型的意见。

</details>

<details>
<summary><b>8 · 披露</b> — 销售者不是独立证人</summary>

<br>

如果嘉宾在卖正在讨论的东西，或这一集是赞助的，这个标记要留在每一条承载结论的引用上。

完成的样子：一集厂商内容不会被读成独立实践。

没有这一步，一次销售谈话会变成证据。

</details>

<details>
<summary><b>9 · Packet</b> — 一个你正在学的问题，对应一个 packet</summary>

<br>

只从已接受的标签刷新 packet。anomaly packet 是 `none` 的池子。一条 claim 对不上时，你去那里看。它不是一个独立主题。

完成的样子：`cited.py packet list` 和你正在学的问题一致。

没有这一步，每次想记起什么，你都从一次新搜索开始。

</details>

<details>
<summary><b>10 · 学习</b> — 回到问题，而不是文件夹</summary>

<br>

`cited.py brief` 把一个问题下已接受的 claim 收在一起。那就是学习这一遍。只有这个 packet 太薄时才去搜索。转写文件夹不是上下文。

完成的样子：你能根据 brief 复述这个问题，而不必打开某一集。

没有这一步，你会再听一遍，或者信任一段模糊的记忆。

</details>

<details>
<summary><b>11 · 三层</b> — 把他们说的和你现在想的分开</summary>

<br>

当你向自己解释一个问题时，把三层分开：你已经冻结的类别、更宽的节目集合、你自己的结论。第三层是你的学习。它不是嘉宾已经证明的事。

完成的样子：你能指出哪一部分是你的。

没有这一步，一个结论会硬化成“播客就是这么说的”。

</details>

<details>
<summary><b>12 · 分母</b> — 知道你真正吸收了多少</summary>

<br>

`cited.py corpus` 会打印你抓了多少集、做了多少张卡、接受了多少条 claim。这是三个不同的数。

完成的样子：你能说出自己指的是哪一个数。

没有这一步，一个下载文件夹会感觉像已经掌握。

</details>

<details>
<summary><b>13 · 漂移</b> — 新类别是写下来的决定</summary>

<br>

按周期看 none 的比例、anomaly packet，以及卡片上的 Gaps。决定是保持、把定义写清楚，还是用一个临时类别扩展。把决定写下来。重新打开开放编码是另一次选择，不是工具因为某一集很怪就给出的建议。

完成的样子：codebook 上有一条带日期的记录，哪怕内容是 “hold”。

没有这一步，一集奇怪的内容就会变成一个新类别。

</details>

<h2 id="recall">回顾</h2>

一个点重要时，回到那一分钟。`cited.py show <id> --at mm:ss --window 1`。引用不超过十五个词。署上说话的人、机构和节目。卡片是转述。时间戳是你返回的方式。

<h2 id="later">以后</h2>

这个库是为你自己的学习而建的。一个问题站稳之后，同一批 packet 可以用于一份笔记、一次演讲、一次交接或一堂课。这些用法集中在 [`LATER.md`](LATER.md)（英文）。

<h2 id="layout">目录</h2>

```text
cited.py           命令
domain.py          读取你的领域包
validate_cards.py  用领域包和转写校验卡片
kbbert.py          本地嵌入，不用 torch
mining/            propose、walk、packets、brief
domain.example/    复制为 domain/ 再改
domain/            你的类别、卡片模式、layer-1、提示词
examples/fixture/  合成转写和一张卡片
transcripts/       你的，不属于这个公开仓库
cards/             你的
AGENT.md           代理可以做什么
LATER.md           一个问题站稳之后可以做什么
```

工作副本里，`transcripts/`、`cards/`、`cited.sqlite` 和 `models/` 被 gitignore。`reindex` 会从文件重建索引。

<h2 id="languages">语言</h2>

页顶那一栏就是语言切换。你正在读的语言是纯文本，其他的是链接。英文是源文本。

一种译文就是一个并列文件：`README.de.md`、`README.zh-CN.md`、`README.ja.md`、`README.ko.md`、`README.fr.md`、`README.es.md`。翻译散文和标题。不翻译命令、标志、文件名、类别 id，以及按键 <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd>。每个文件的标题 id 相同，所以换语言之后 `#quick-start` 仍然有效。

要增加一种语言，复制 `README.md`，翻译散文，并在该文件自己的语言栏里用 `<strong>` 标出这种语言。

<h2 id="license">许可</h2>

代码为 [MIT](LICENSE)。BGE 权重和 Whisper 模型是单独下载的，各有许可。你抓取的转写不会因本项目而被重新许可。

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <strong>한국어</strong> ·
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

<p>팟캐스트와 강연을 넣는다. 스스로 배우는 지식 베이스가 된다.</p>

<p>임베딩은 제안한다. 받아들이는 것은 사람이다.</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="MIT 라이선스" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="받아쓴 글은 내 컴퓨터에 둔다" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">빠른 시작</a> ·
  <a href="#the-loop">흐름</a> ·
  <a href="#human-work">사람이 할 일</a> ·
  <a href="#recall">되짚기</a> ·
  <a href="#later">나중</a> ·
  <a href="#layout">구성</a>
</p>
</div>

---

<h2 id="quick-start">빠른 시작</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

Python 3.9 이상, SQLite FTS5 (macOS와 python.org 빌드에 보통 들어 있다). 픽스처는 합성이라, 아무것도 받기 전에 동작한다. Whisper와 태거는 선택이다. 둘 다 아래를 본다.

<h2 id="the-loop">흐름</h2>

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

`propose`는 후보를 쓴다. `walk`에서 태그는 내가 아는 것의 일부가 된다. 받아들인 태그만 packet에 들어간다. `brief`는 에피소드를 다시 듣지 않고 한 질문으로 돌아가는 방법이다.

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

에이전트는 카드를 초안하고 brief에서 질문을 다시 꺼낼 수 있다. 태그를 받아들이거나, 범주를 만들거나, 배운 것을 요약하려고 대본 전체를 읽지는 못한다. 짧은 계약은 [`AGENT.md`](AGENT.md)이다 (영어, 규칙은 같다).

<h2 id="what-this-is">이것이 무엇인지</h2>

| 이것 | 이것이 아님 |
|---|---|
| 스스로 배우는 로컬 지식 베이스. 팟캐스트와 강연이 다시 돌아갈 수 있는 claim이 된다 | 호스팅된 코퍼스, 또는 다른 사람의 끝난 강의 |
| 얇은 카드와 색인. 녹음을 다시 듣지 않아도 된다 | 요약 기계 |
| 직접 쓰는 codebook, 그다음의 제안기 | 자동 태거 |
| 사람의 walk, 그리고 다시 펼칠 수 있는 packet | 오픈 코딩을 대신하는 앱 |

<h2 id="rights">권리</h2>

받아쓴 글은 가져온 기계에 둔다. 그것을 보유할 권리가 필요하다. 다른 사람의 말을 커밋하지 않는다. 이 저장소가 담는 것은 합성 픽스처와 빈 도메인 팩뿐이다. 자료, 카드, 태그는 자신의 것이고, 비공개 작업 복사본에 둔다.

<h2 id="setup">설치</h2>

<h3 id="setup-video">영상</h3>

빠른 시작의 `yt-dlp`와 `youtube-transcript-api`면 자막은 충분하다. YouTube가 로그인을 요구하면 `cited.py add`에 `--cookies-from-browser chrome`을 붙인다. 사이트가 바뀐 뒤 가져오기가 깨지면 `yt-dlp`를 올린다.

<h3 id="setup-podcasts">팟캐스트</h3>

피드에 대본이 있으면 그대로 쓴다. 없으면 오디오를 로컬에서 받아쓴다. 업로드하지 않는다.

```bash
# Apple Silicon
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# 그 밖
python3 -m pip install -U faster-whisper
```

첫 받아쓰기는 Whisper 모델을 받는다 (약 1.5 GB). 어휘 힌트는 `domain/whisper_prompt.txt`에 둔다. 예시 프롬프트는 일반적이다. 분야의 고유명으로 바꾸지 않으면 그 이름을 잘못 듣는다.

<h3 id="setup-tagging">태깅</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# BAAI/bge-small-en-v1.5 를 models/bge-small 에 받는다
# (MIT). 가중치는 이 저장소에 없다.
```

`cited.py mine propose`는 이 로컬 모델을 쓴다. 없어도 검색, 카드, brief는 동작한다. 손으로 태그를 달거나, 모델을 설치한다.

<h3 id="setup-domain">도메인 팩</h3>

```bash
cp -R domain.example domain
```

규모 있게 태그하기 전에 네 가지를 고친다.

- `domain/categories.json` — id, name, definition, aliases. 두 개는 자리표시이다.
- `domain/card.json` — 주제와 카드의 닫힌 어휘.
- `domain/layer1.md` — 한 단락. 이 질문에 대해 지금 품고 있는 것과, 품고 있지 않은 것.
- `domain/whisper_prompt.txt` — 받아쓰기가 예상해야 할 이름과 용어.

<h2 id="first-hour">첫 한 시간</h2>

1. 빠른 시작을 실행하고 픽스처가 검색되는지 확인한다.
2. 보유할 권리가 있는 자료를 하나 가져온다. 받기 전에 목록을 본다.

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests`, 그다음 `?`가 없어질 때까지 `python3 cited.py meta <id> --guest "…" --role "…" --company "…"`.
4. 멈춘다. 카드를 쓴다. 아직 `propose`하지 않는다.

<h2 id="human-work">사람이 할 일</h2>

명령은 빈 이론과, 다시 돌아가지 않을 에피소드 더미에서도 돌아간다. 이 단계들이 베이스를 배울 수 있는 것으로 만든다. 각각에 끝난 상태가 있다. 건너뛰면 실패는 구체적이다.

<details>
<summary><b>1 · 렌즈</b> — 받기 전에 질문을 쓴다</summary>

<br>

질문을 쓰고, 무엇이 들어올 수 있는지 규칙을 쓴다. 질문과 관련이 있을 것. 총정리와 베스트는 빼기. 같은 게스트는 많아야 두 번. 반대하는 목소리는 남기기.

끝난 상태: 다른 사람이 그 규칙을 새 에피소드에 적용할 수 있다.

이것이 없으면 코퍼스는 피드가 올린 전부이다.

</details>

<details>
<summary><b>2 · 수집</b> — 목록을 보고 가져온 뒤, 프로그램에 태그를 단다</summary>

<br>

먼저 `pod --list` 또는 `queue`. 가져올 때 프로그램에 태그를 단다.

끝난 상태: `transcripts/`의 모든 파일이 카드로 만들 것이다.

이것이 없으면 인코딩하지 않을 시간을 받아쓰게 된다.

</details>

<details>
<summary><b>3 · 이름</b> — 음성 인식은 사람과 숫자를 틀린다</summary>

<br>

`cited.py guests`, 그다음 모든 `?`에 `cited.py meta`. 이름과 숫자를 쇼 노트와 맞춘다.

끝난 상태: 인용이 올바른 사람을 가리킨다.

이것이 없으면 다른 사람에게 공을 돌리게 된다.

</details>

<details>
<summary><b>4 · 얇은 카드</b> — 카드가 증거이고, 대본은 확인이다</summary>

<br>

에이전트는 `cited.py card-scaffold`로 초안할 수 있다. 검증은 `validate_cards.py`. 바꿔 말한다. 타임스탬프는 대본 문단의 시작이어야 한다. 인용은 많아야 둘, 짧고, 그대로.

끝난 상태: 검증기가 조용하고 `reindex`가 새 claim을 보여 준다.

이것이 없으면 색인은 허구이다.

</details>

<details>
<summary><b>5 · Codebook</b> — 자신의 자료로 쓰고, 그다음 propose를 켠다</summary>

<br>

열다섯 편쯤 읽는다. 범주는 자신의 말로 쓴다. id, name, definition, aliases. 표본은 손으로 태그한다. 오픈 코딩 전체는 별도의 일이고, 비싸다. `domain.example`의 자리표시는 이론이 아니다.

끝난 상태: 점수를 보지 않고 각 범주를 설명할 수 있다.

이것이 없으면 자리표시로, 또는 다른 사람의 질문으로 코퍼스를 태그하게 된다.

</details>

<details>
<summary><b>6 · 보정</b> — 불명확한 범주는 기본 대기열에서 빠진다</summary>

<br>

`domain/calibration.jsonl`에서 각 범주를 clear, fuzzy, unclear로 표시한다. unclear은 `--include-unclear`를 주지 않으면 `mine walk`에 나오지 않는다.

끝난 상태: 대기열에는 적용할 수 있는 범주만 있다.

이것이 없으면 검토 시간이 적용할 수 없는 것에 가라앉는다.

</details>

<details>
<summary><b>7 · Walk</b> — 받아들임은 사람이 누르는 키</summary>

<br>

<kbd>a</kbd> accept, <kbd>r</kbd> reject, <kbd>n</kbd> none, <kbd>s</kbd> skip, <kbd>q</kbd> quit. 모르겠으면 skip. reject는 claim과 범주를 둘 다 이해했을 때만. 일괄 accept는 없다.

끝난 상태: 받아들인 각 줄을 소리 내어 말할 수 있다.

이것이 없으면 숫자는 모델의 의견이다.

</details>

<details>
<summary><b>8 · 공개</b> — 판매자는 독립된 증인이 되지 않는다</summary>

<br>

게스트가 논의 중인 것을 팔거나, 에피소드가 후원되었다면, 그 표시는 발견을 실어 나르는 모든 인용에 남긴다.

끝난 상태: 벤더 에피소드를 독립된 실천으로 읽을 수 없다.

이것이 없으면 판매 대화가 증거가 된다.

</details>

<details>
<summary><b>9 · Packet</b> — 배우고 있는 질문마다 하나</summary>

<br>

packet은 받아들인 태그에서만 새로 고친다. anomaly packet은 `none`의 웅덩이이다. claim이 맞지 않았을 때 보는 곳이며, 그 자체로 주제가 아니다.

끝난 상태: `cited.py packet list`가 지금 공부하는 질문과 맞다.

이것이 없으면, 떠올리고 싶을 때마다 새 검색에서 시작한다.

</details>

<details>
<summary><b>10 · 공부</b> — 질문으로 돌아간다. 폴더로 돌아가지 않는다</summary>

<br>

`cited.py brief`는 한 질문에 대해 받아들인 claim을 모은다. 그것이 공부하는 한 번이다. 검색은 그 packet이 얇을 때만. 대본 폴더는 맥락이 아니다.

끝난 상태: 에피소드를 열지 않고 brief에서 질문을 다시 말할 수 있다.

이것이 없으면 다시 듣거나, 흐린 기억을 믿게 된다.

</details>

<details>
<summary><b>11 · 세 층</b> — 그들이 말한 것과 지금 생각하는 것을 가른다</summary>

<br>

질문을 스스로에게 설명할 때는 세 층을 가른다. 얼린 범주, 더 넓은 에피소드, 자신의 결론. 세 번째는 자신의 배움이다. 게스트가 증명한 것이 아니다.

끝난 상태: 어느 부분이 자신의 것인지 가리킬 수 있다.

이것이 없으면 결론이 "팟캐스트가 그렇게 말했다"로 굳는다.

</details>

<details>
<summary><b>12 · 분모</b> — 실제로 받아들인 양을 안다</summary>

<br>

`cited.py corpus`는 가져온 편수, 카드로 만든 편수, 받아들인 claim 수를 출력한다. 이것은 서로 다른 수이다.

끝난 상태: 어느 수를 말하는지 말할 수 있다.

이것이 없으면 다운로드 폴더가 숙달처럼 느껴진다.

</details>

<details>
<summary><b>13 · 드리프트</b> — 새 범주는 적어 둔 결정이다</summary>

<br>

주기로 none 비율, anomaly packet, 카드의 Gaps를 읽는다. 유지할지, 정의를 분명히 할지, 임시 범주로 넓힐지 정한다. 결정을 적는다. 오픈 코딩을 다시 여는 것은 별도의 선택이며, 한 편이 이상하다고 도구가 권하는 일이 아니다.

끝난 상태: codebook에 날짜가 있는 메모가 있다. 메모가 "hold"여도 된다.

이것이 없으면 이상한 한 편이 새 범주가 된다.

</details>

<h2 id="recall">되짚기</h2>

한 점이 중요하면 그 분으로 돌아간다. `cited.py show <id> --at mm:ss --window 1`. 인용은 열다섯 단어 아래. 말한 사람, 조직, 프로그램을 밝힌다. 카드는 바꿔 말한 것이다. 타임스탬프가 돌아가는 방법이다.

<h2 id="later">나중</h2>

이 베이스는 자신의 학습을 위한 것이다. 질문이 자리 잡으면 같은 packet이 메모, 강연, 인수인계, 수업에 쓰인다. 그 쓰임은 [`LATER.md`](LATER.md) (영어)에 모아 두었다.

<h2 id="layout">구성</h2>

```text
cited.py           명령
domain.py          도메인 팩을 읽는다
validate_cards.py  도메인 팩과 대본에 대해 카드를 검사
kbbert.py          로컬 임베딩, torch 없음
mining/            propose, walk, packets, brief
domain.example/    domain/ 으로 복사한 뒤 편집
domain/            범주, 카드 스키마, layer-1, 프롬프트
examples/fixture/  합성 대본과 카드
transcripts/       자신의 것. 이 공개 저장소에 넣지 않는다
cards/             자신의 것
AGENT.md           에이전트가 해도 되는 일
LATER.md           질문이 자리 잡은 뒤에 할 수 있는 일
```

작업 복사본에서 `transcripts/`, `cards/`, `cited.sqlite`, `models/`는 gitignore된다. `reindex`는 파일에서 색인을 다시 만든다.

<h2 id="languages">언어</h2>

맨 위 막대가 언어 전환이다. 읽고 있는 언어는 일반 텍스트이고, 나머지는 링크이다. 영어가 원문이다.

번역은 형제 파일이다. `README.de.md`, `README.zh-CN.md`, `README.ja.md`, `README.ko.md`, `README.fr.md`, `README.es.md`. 산문과 제목을 옮긴다. 명령, 플래그, 파일 이름, 범주 id, 키 <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd>는 옮기지 않는다. 제목 id는 모든 파일에서 같으므로, 언어를 바꿔도 `#quick-start`는 그대로다.

언어를 더하려면 `README.md`를 복사하고, 산문을 옮기고, 그 파일의 막대에서 그 언어를 `<strong>`로 표시한다.

<h2 id="license">라이선스</h2>

코드는 [MIT](LICENSE)이다. BGE 가중치와 Whisper 모델은 따로 받으며, 라이선스도 따로다. 가져온 대본이 이 프로젝트 때문에 다시 라이선스되지는 않는다.

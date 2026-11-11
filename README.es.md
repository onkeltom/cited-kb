<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.zh-CN.md">简体中文</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.ko.md">한국어</a> ·
  <a href="README.fr.md">Français</a> ·
  <strong>Español</strong>
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

<p>Entran podcasts y charlas. Una base de conocimiento para aprender.</p>

<p>Los embeddings proponen. Una persona acepta.</p>

<p>
  <a href="https://www.python.org/"><img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="LICENSE"><img alt="licencia MIT" src="https://img.shields.io/badge/license-MIT-111111?style=flat-square"></a>
  <a href="#rights"><img alt="Las transcripciones se quedan en tu máquina" src="https://img.shields.io/badge/transcripts-stay%20local-2F6F4E?style=flat-square"></a>
</p>

<p>
  <a href="#quick-start">Inicio rápido</a> ·
  <a href="#the-loop">El ciclo</a> ·
  <a href="#human-work">El trabajo humano</a> ·
  <a href="#recall">Volver</a> ·
  <a href="#later">Después</a> ·
  <a href="#layout">Estructura</a>
</p>
</div>

---

<h2 id="quick-start">Inicio rápido</h2>

```bash
git clone https://github.com/onkeltom/cited-kb.git
cd cited-kb
python3 -m pip install -U yt-dlp youtube-transcript-api
cp -R domain.example domain
python3 cited.py reindex
python3 validate_cards.py examples/fixture/cards examples/fixture/transcripts
python3 cited.py search "fixture"
```

Python 3.9 o más nuevo, con SQLite FTS5 (los builds habituales de macOS y python.org). La fixture es sintética, así que esto corre antes de traer nada. Whisper y el etiquetador son opcionales. Los dos están más abajo.

<h2 id="the-loop">El ciclo</h2>

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

`propose` escribe candidatos. `walk` es donde una etiqueta pasa a formar parte de lo que sabes. Solo las etiquetas aceptadas entran en un packet. `brief` es cómo te vuelves a sentar con una pregunta, sin volver a oír los episodios.

```text
$ python3 cited.py mine walk --category G02

  ex-01   12:40   G02   0.61
  they measure licenses and call it adoption

  [a]ccept   [r]eject   [n]one   [s]kip   [q]uit
```

Un agente puede redactar fichas y volver a sacar una pregunta desde un brief. No puede aceptar una etiqueta, inventar una categoría, ni leer una transcripción entera para resumir lo que aprendiste. La versión corta de ese contrato está en [`AGENT.md`](AGENT.md) (en inglés; las reglas son las mismas).

<h2 id="what-this-is">Qué es esto</h2>

| Esto es | Esto no es |
|---|---|
| Una base local para aprender: los podcasts y las charlas se vuelven claims a los que vuelves | Un corpus alojado, o el curso ya hecho de otra persona |
| Fichas delgadas y un índice, para no volver a oír la grabación | Una máquina de resúmenes |
| Un codebook que escribes tú, y después un proponente | Un etiquetador automático |
| Un walk humano, y luego packets que vuelves a abrir | Una app que hace open coding por ti |

<h2 id="rights">Derechos</h2>

Las transcripciones se quedan en la máquina que las trajo. Hace falta el derecho a conservarlas. No hagas commit de las palabras de otras personas. Este repositorio trae una fixture sintética y un domain pack vacío. Tus fuentes, fichas y etiquetas son tuyas, y van en tu copia de trabajo privada.

<h2 id="setup">Puesta en marcha</h2>

<h3 id="setup-video">Vídeo</h3>

`yt-dlp` y `youtube-transcript-api`, del inicio rápido, bastan para los subtítulos. Si YouTube pide iniciar sesión, añade `--cookies-from-browser chrome` a `cited.py add`. Si una descarga se rompe tras un cambio del sitio, actualiza `yt-dlp`.

<h3 id="setup-podcasts">Podcasts</h3>

Un feed que trae transcripción se usa tal cual. Si no, el audio se transcribe en local. No se sube nada.

```bash
# Apple Silicon
brew install ffmpeg
python3 -m pip install -U mlx-whisper

# en cualquier otro caso
python3 -m pip install -U faster-whisper
```

La primera transcripción descarga un modelo de Whisper (unos 1,5 GB). La pista de vocabulario va en `domain/whisper_prompt.txt`. El ejemplo es genérico. Cámbialo por los nombres propios de tu campo, o se oirán mal.

<h3 id="setup-tagging">Etiquetado</h3>

```bash
python3 -m venv .venv
.venv/bin/pip install -U numpy safetensors tokenizers
# descarga BAAI/bge-small-en-v1.5 en models/bge-small
# (MIT). Los pesos no están en este repo.
```

`cited.py mine propose` usa ese modelo local. Sin él, la búsqueda, las fichas y los briefs siguen funcionando. Etiquetas a mano, o instalas el modelo.

<h3 id="setup-domain">Tu domain pack</h3>

```bash
cp -R domain.example domain
```

Cuatro cosas que editar antes de etiquetar a escala:

- `domain/categories.json` — id, name, definition, aliases. Los dos ejemplos son marcadores.
- `domain/card.json` — topics y los vocabularios cerrados de una ficha.
- `domain/layer1.md` — un párrafo: lo que sostienes ahora sobre esta pregunta, y lo que no.
- `domain/whisper_prompt.txt` — nombres y términos que el transcriptor debe esperar.

<h2 id="first-hour">La primera hora</h2>

1. Corre el inicio rápido y confirma que la fixture se busca.
2. Trae una fuente que tengas derecho a conservar. Lista antes de descargar.

```bash
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --list
python3 cited.py pod "<rss-or-apple-url>" --latest 20 --pick 3 --tags my-show
```

3. `python3 cited.py guests`, luego `python3 cited.py meta <id> --guest "…" --role "…" --company "…"` hasta que desaparezcan los interrogantes.
4. Para. Escribe la ficha. Todavía no hagas `propose`.

<h2 id="human-work">El trabajo humano</h2>

Los comandos corren igual con una teoría vacía y una pila de episodios a los que no vas a volver. Estos pasos hacen de la base algo de lo que aprendes. Cada uno tiene un estado de terminado. Saltarlo produce un fallo concreto.

<details>
<summary><b>1 · Lente</b> — escribe la pregunta antes de descargar</summary>

<br>

Escribe la pregunta y luego las reglas de lo que puede entrar: tiene que ver con la pregunta, los recap y los best-of se quedan fuera, el mismo invitado aparece como mucho dos veces, las voces que discrepan se quedan.

Terminado cuando otra persona podría aplicar las reglas a un episodio nuevo.

Sin esto, el corpus es lo que publicó el feed.

</details>

<details>
<summary><b>2 · Ingesta</b> — lista, luego trae, y etiqueta el programa</summary>

<br>

Primero `pod --list` o `queue`. Etiqueta el programa al entrar.

Terminado cuando cada archivo de `transcripts/` es uno que piensas fichar.

Sin esto, transcribes horas que no vas a codificar.

</details>

<details>
<summary><b>3 · Nombres</b> — el reconocimiento de voz miente sobre personas y cifras</summary>

<br>

`cited.py guests`, luego `cited.py meta` para cada `?`. Contrasta nombres y números con las notas del programa.

Terminado cuando una cita nombraría a la persona correcta.

Sin esto, acreditas a la persona equivocada.

</details>

<details>
<summary><b>4 · Fichas delgadas</b> — la ficha es la prueba, la transcripción es la comprobación</summary>

<br>

Un agente puede redactar desde `cited.py card-scaffold`. Tú corres `validate_cards.py`. Parafrasea. Cada marca de tiempo tiene que ser el inicio de un párrafo en la transcripción. Dos citas como mucho, cortas y literales.

Terminado cuando el validador calla y `reindex` muestra los claims nuevos.

Sin esto, el índice es ficción.

</details>

<details>
<summary><b>5 · Codebook</b> — escríbelo desde tus fuentes, y luego enciende propose</summary>

<br>

Lee unas quince fuentes. Escribe las categorías con tus palabras: id, name, definition, aliases. Etiqueta una muestra a mano. Un pase completo de open coding es otro proyecto, y caro. Los marcadores de `domain.example` no son una teoría.

Terminado cuando puedes explicar cada categoría sin mirar una puntuación.

Sin esto, etiquetas el corpus con los ejemplos, o con la pregunta de otra persona.

</details>

<details>
<summary><b>6 · Calibrar</b> — las categorías dudosas salen de la cola por defecto</summary>

<br>

Marca cada categoría como clear, fuzzy o unclear en `domain/calibration.jsonl`. Unclear se queda fuera de `mine walk` salvo que pases `--include-unclear`.

Terminado cuando la cola solo tiene categorías que sabes aplicar.

Sin esto, el tiempo de revisión se hunde en las que no sabes aplicar.

</details>

<details>
<summary><b>7 · Walk</b> — aceptar es una tecla humana</summary>

<br>

<kbd>a</kbd> accept, <kbd>r</kbd> reject, <kbd>n</kbd> none, <kbd>s</kbd> skip, <kbd>q</kbd> quit. Dudar significa skip. Reject solo cuando entiendes el claim y la categoría. No hay accept masivo.

Terminado cuando cada fila aceptada es una que dirías en voz alta.

Sin esto, los recuentos son la opinión del modelo.

</details>

<details>
<summary><b>8 · Divulgación</b> — quien vende no se vuelve un testigo independiente</summary>

<br>

Si el invitado vende lo que se está discutiendo, o el episodio es patrocinado, esa marca se queda en cada cita que carga un hallazgo.

Terminado cuando un episodio de un vendor no se puede leer como práctica independiente.

Sin esto, una conversación de ventas se vuelve evidencia.

</details>

<details>
<summary><b>9 · Packets</b> — un packet por pregunta que estás aprendiendo</summary>

<br>

Refresca los packets solo desde etiquetas aceptadas. El packet anomaly es el conjunto de los `none`. Es donde miras cuando un claim no encajó. No es un tema propio.

Terminado cuando `cited.py packet list` coincide con las preguntas que de verdad estás estudiando.

Sin esto, cada vez que quieres recordar empiezas por una búsqueda nueva.

</details>

<details>
<summary><b>10 · Estudio</b> — vuelve a la pregunta, no a la carpeta</summary>

<br>

`cited.py brief` reúne los claims aceptados de una pregunta. Esa es la pasada de estudio. La búsqueda es para cuando ese packet es fino. La carpeta de transcripciones no es el contexto.

Terminado cuando puedes volver a decir la pregunta desde el brief sin abrir un episodio.

Sin esto, vuelves a escuchar, o confías en un recuerdo vago.

</details>

<details>
<summary><b>11 · Tres capas</b> — separa lo que dijeron de lo que ahora piensas</summary>

<br>

Cuando te explicas una pregunta, separa tres capas: las categorías que congelaste, el conjunto más amplio de episodios, y tu propia conclusión. La tercera es tu aprendizaje. No es algo que los invitados hayan probado.

Terminado cuando puedes señalar qué parte es tuya.

Sin esto, una conclusión se endurece en «los podcasts lo dijeron».

</details>

<details>
<summary><b>12 · Denominadores</b> — sabe cuánto has tomado de verdad</summary>

<br>

`cited.py corpus` imprime cuántos episodios trajiste, cuántos fichaste y cuántos claims aceptaste. Son recuentos distintos.

Terminado cuando puedes decir qué recuento estás usando.

Sin esto, una carpeta de descargas se siente como dominio.

</details>

<details>
<summary><b>13 · Deriva</b> — una categoría nueva es una decisión escrita</summary>

<br>

Con una cadencia, lee la tasa de none, el packet anomaly y los Gaps de las fichas. Decide mantener, aclarar una definición, o extender con una categoría provisional. Escribe la decisión. Reabrir el open coding es una elección aparte, no una sugerencia de la herramienta porque un episodio fue raro.

Terminado cuando el codebook tiene una nota con fecha, también cuando la nota es «hold».

Sin esto, un episodio extraño se vuelve una categoría nueva.

</details>

<h2 id="recall">Volver</h2>

Cuando un punto importa, vuelve al minuto. `cited.py show <id> --at mm:ss --window 1`. Una cita se queda por debajo de quince palabras. Acredita a quien habla, a la organización y al programa. La ficha es una paráfrasis. La marca de tiempo es cómo vuelves.

<h2 id="later">Después</h2>

La base es para tu propio aprendizaje. Cuando una pregunta ya está firme, los mismos packets sirven para una nota, una charla, un traspaso o una clase. Esos usos están reunidos en [`LATER.md`](LATER.md) (en inglés).

<h2 id="layout">Estructura</h2>

```text
cited.py           el comando
domain.py          carga tu paquete de dominio
validate_cards.py  fichas contra el domain pack y la transcripción
kbbert.py          embeddings locales, sin torch
mining/            propose, walk, packets, brief
domain.example/    copiar a domain/ y editar
domain/            tus categorías, el esquema de ficha, la layer-1, el prompt
examples/fixture/  transcripción sintética y una ficha
transcripts/       tuyo, no para este repo público
cards/             tuyo
AGENT.md           lo que un agente puede hacer
LATER.md           ideas para cuando una pregunta ya está firme
```

En una copia de trabajo, `transcripts/`, `cards/`, `cited.sqlite` y `models/` están en gitignore. `reindex` reconstruye el índice desde los archivos.

<h2 id="languages">Idiomas</h2>

La barra de arriba es el cambio de idioma. El idioma que estás leyendo es texto plano. Los otros son enlaces. El inglés es el texto fuente.

Una traducción es un archivo hermano: `README.de.md`, `README.zh-CN.md`, `README.ja.md`, `README.ko.md`, `README.fr.md`, `README.es.md`. Se traduce la prosa y los títulos. No se traducen los comandos, las flags, los nombres de archivo, los ids de categoría, ni las teclas <kbd>a</kbd> <kbd>r</kbd> <kbd>n</kbd> <kbd>s</kbd> <kbd>q</kbd>. Los ids de título son los mismos en cada archivo, así que `#quick-start` sobrevive al cambio de idioma.

Para añadir un idioma, copia `README.md`, traduce la prosa, y marca ese idioma con `<strong>` en su propia barra.

<h2 id="license">Licencia</h2>

El código es [MIT](LICENSE). Los pesos de BGE y los modelos de Whisper son descargas aparte, con sus propias licencias. Las transcripciones que traigas no quedan relicenciadas por este proyecto.

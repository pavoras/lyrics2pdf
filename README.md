# lyrics2pdf

Turn a plain-text lyric file into a clean, printable one-page lyric sheet, with room above every line to pencil in chords.

![Example output](examples/preview.png)

## Features

- **Auto-fit spacing.** A binary search finds the largest line spacing that still fits the whole song on **one A4 page**. The extra space goes *above* each line, where chords go.
- **Chorus detection.** Tag sections yourself (`[Verse]`, `[Chorus]`, `[Bridge]` ...), or leave them untagged: any stanza that repeats is styled as a chorus, the rest are numbered verses.
- **One or two columns** (`--cols 2`) for long songs.
- A single file, one dependency ([ReportLab](https://www.reportlab.com/)).

## Usage

```bash
pip install -r requirements.txt
python lyrics2pdf.py song.txt -t "Title" -a "Artist" [-o out.pdf] [--cols 2] [--leading PT]
```

| Option | Default | Meaning |
| --- | --- | --- |
| `-t`, `--title` | file name | Song title |
| `-a`, `--artist` | none | Artist line under the title |
| `-o`, `--out` | `song.pdf` | Output path |
| `--cols` | `1` | `1` or `2` columns |
| `--leading` | auto | Fixed line spacing in pt instead of auto-fit |

Try the bundled example:

```bash
python lyrics2pdf.py examples/auld_lang_syne.txt -a "Robert Burns" --cols 2
```

## Input format

Stanzas are separated by blank lines. Section tags are optional and go on their own line:

```
[Verse 1]
First line of the verse
Second line of the verse

[Chorus]
Chorus line one
Chorus line two
```

Requires Python 3.10+.

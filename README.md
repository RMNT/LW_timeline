# LW manuscript timeline

An interactive, zoomable timeline of Wittgenstein manuscript entries. The data comes
from an RDF (Turtle) file queried with SPARQL, the server is FastAPI, and the chart is
drawn with D3.

- **Exact dates** are drawn as circles.
- **Estimated dates** (a range, e.g. "Aug – Sep 1915") are drawn as a diamond at the
  middle of the range, with a bar along the axis showing the whole range.
- Entries that are close together are merged into one numbered circle. Click it to zoom
  in on exactly those entries.
- Two checkboxes show only exact dates, only estimated dates, or both.

## Run it

You need Python 3 and the data file (see below).

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

1. Put the data file, named `read_gsp`, in this folder (next to `main.py`).
2. Start the server **from this folder**:

   ```
   uvicorn main:app
   ```

3. Open <http://127.0.0.1:8000/timeline>.

The first start is slow and needs a lot of memory, because the whole data file is
loaded into memory. `static/timeline_data.js` is generated from the data file
(`generate_js.py`), so it is not stored in the repository. The page loads D3 from a CDN,
so it needs an internet connection.

## Data

The data file `read_gsp` is not included in this repository.

> Download it from https://wab.uib.no/

## Files

| File | What it does |
|---|---|
| `main.py` | the FastAPI app and its routes |
| `queries.py` | the SPARQL queries (`exact_ms`, `range_ms`) |
| `generate_js.py` | runs the queries and writes `static/timeline_data.js` |
| `texts.py` | the chart code (JavaScript) that `generate_js.py` appends to the data |
| `templates/timeline.html` | the page |

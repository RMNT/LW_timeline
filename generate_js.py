from queries import exact_ms, range_ms
from pyoxigraph import Store, RdfFormat
from collections import defaultdict
from texts import finish
import json

store = Store()

with open("read_gsp", "rb") as f:
    store.load(f, RdfFormat.TURTLE)

def _label(result):
    # the label, or (if the entry has none) the last part of its IRI
    if result['ms_label']:
        return str(result['ms_label'])[1:-1]
    return str(result['remark'])[1:-1].rsplit("/", 1)[-1]

def gen_dates():
    # (start, end, title, link); end is None for an exact date.
    # One row per remark: if it has an exact :created date, that wins.
    entries = {}

    for result in store.query(exact_ms):
        entries[str(result['remark'])] = (
            str(result['created'])[1:].split('"')[0],
            None,
            _label(result),
            str(result['link'])[1:-1],
        )

    for result in store.query(range_ms):
        key = str(result['remark'])
        if key in entries:
            continue
        entries[key] = (
            str(result['madeAfter'])[1:].split('"')[0],
            str(result['madeBefore'])[1:].split('"')[0],
            _label(result),
            str(result['link'])[1:-1],
        )

    return sorted(entries.values(), key=lambda x: (x[0], x[2]))


def aggr_dates(date_ms):
    grouped = defaultdict(list)
    for date, label, link in date_ms:
        grouped[date].append((label, link))

    aggregated = []
    for date, entries in sorted(grouped.items()):
        labels_text = ", ".join(f"{label}" for label, link in entries[:5])
        first_link = entries[0][1]  # just use the first link for the aggregated point
        text = f"{len(entries)} entries: {labels_text}" + ("..." if len(entries) > 5 else "")
        aggregated.append((date, text, first_link))
    return aggregated


def gen_js(ls):
    start = """const RAW_DATA = [
    """

    lines = []
    for date, end, ms, link in ls:          # ls holds (start, end, title, link)
        entry = {"date": date, "end": end, "title": ms, "link": link}
        lines.append("  " + json.dumps(entry, ensure_ascii=False) + ",\n")
    middle = "".join(lines)

    final_file = start + middle + finish

    with open("static/timeline_data.js", "w", encoding="utf-8") as f:
        f.write(final_file)

def generate_full_js():
    dates = gen_dates()
    # dates = aggr_dates(dates)
    gen_js(dates)
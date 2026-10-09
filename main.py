from pyoxigraph import Store, RdfFormat
from fastapi import FastAPI, Request
import os
from fastapi import Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
from generate_js import generate_full_js
from datetime import datetime
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter
from queries import range_ms, exact_ms

store = Store()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Serve the saved chart image as a static file
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/details", response_class=HTMLResponse)
def show_details(request: Request, date: str = Query(...)):
    store = Store()
    with open("read_gsp", "rb") as f:
        store.load(f, RdfFormat.TURTLE)

    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX : <http://purl.org/wittgensteinsource/ont/>

    SELECT ?ms_label ?htmlView
    WHERE {
      ?remark :created ?created ;
              rdfs:label ?ms_label ;
              :hasHtmlView ?htmlView .
      FILTER (STR(?created) = "%s")
    }
    """ % date

    entries = [
        {
            "label": str(result["ms_label"])[1:-1],
            "url": str(result["htmlView"])[1:-1]
        }
        for result in store.query(query)
    ]

    return templates.TemplateResponse(
        request=request, name="details.html", context={"date": date, "entries": entries}
    )


# @app.get('/timeline', response_class=HTMLResponse)
# def get_timeline_item(request: Request):
#     pass


@app.get('/timeline', response_class=HTMLResponse)
def get_timeline(request: Request):
    if not os.path.exists("static/timeline_data.js"):
        print('failas nerastas')
        generate_full_js()

    items = []
    for i, result in enumerate(store.query(exact_ms)):
        created_str = str(result["created"]).split('-')[1]
        label = str(result.get("ms_label", '"Unknown"'))[1:-1]
        link = str(result.get('link', "'Unknown'"))[1:-1]

        items.append({
            "id": i,
            "content": label,
            "start": created_str,
            'link': link
        })
    timeline_data = json.dumps(items)
    return FileResponse("templates/timeline.html")


@app.get("/day_ranges", response_class=HTMLResponse)
def show_results(request: Request):
    if not os.path.exists("static/mano_grafikas.png"):
        with open("read_gsp", "rb") as f:
            store.load(f, RdfFormat.TURTLE)

        unclear_dates = [
            (str(result["after"]).split('"')[1], str(result['before']).split('"')[1], str(result['ms_label'])[1:-1])
            for result in store.query(range_ms)
        ]

        day_ranges = []
        for date in unclear_dates:
            after, before, label = date
            after, before = datetime.strptime(after, "%Y-%m-%d").date(), datetime.strptime(before, "%Y-%m-%d").date()
            day_ranges.append(((before - after).days, label))

        ranges_counter = Counter(r[0] for r in day_ranges)
        ranges_counter = sorted(ranges_counter.items())

        x, y = [], []
        for r in ranges_counter:
            x.append(r[0])
            y.append(r[1])

        # plt.xticks(x)

        plt.bar(x, y, width=50)
        plt.xscale("log")
        plt.xlabel("Day range")
        plt.ylabel("Count")
        plt.title("Distribution of date range spans")
        plt.savefig("static/mano_grafikas.png", dpi=300, bbox_inches="tight")
        plt.close()

        return templates.TemplateResponse(
        request=request, name="chart.html", context={})
    return templates.TemplateResponse(request=request, name="chart.html", context={})
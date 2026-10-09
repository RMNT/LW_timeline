finish = "];\n\n" + r"""
const STEM_MIN = 34;
const STEM_MAX = 298;

function computeHeightScale(clusters) {
  const maxCount = d3.max(clusters, (c) => c.items.length) || 1;
  return d3.scaleLog()
    .domain([1, Math.max(maxCount, 2)])
    .range([STEM_MIN, STEM_MAX])
    .clamp(true);
}

function parseISODate(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

const DATA = RAW_DATA
  .map((d) => {
    const date = parseISODate(d.date);
    const endDate = d.end ? parseISODate(d.end) : null;
    const isRange = !!endDate && endDate > date;
    const mid = isRange ? new Date((date.getTime() + endDate.getTime()) / 2) : date;
    return { ...d, date, endDate: isRange ? endDate : null, isRange, mid };
  })
  .sort((a, b) => a.mid - b.mid);

const dateGroups = new Map();
DATA.forEach((d) => {
  const key = d.mid.getTime();
  if (!dateGroups.has(key)) dateGroups.set(key, []);
  dateGroups.get(key).push(d);
});
dateGroups.forEach((group) => {
  group.sort((a, b) => a.title.localeCompare(b.title, "en", { numeric: true }));
  group.forEach((d, i) => {
    d.plotDate = new Date(d.mid.getTime() + i * 1000 * 60 * 60 * 4);
    d.t = d.plotDate.getTime(); // numeric copy, so clustering can avoid Date objects
  });
});

DATA.sort((a, b) => a.plotDate - b.plotDate);

const filterState = { exact: true, range: true };
let activeData = DATA;
function applyFilter() {
  activeData = DATA.filter((d) => (d.isRange ? filterState.range : filterState.exact));
}

const MARKER_COLOR = "#3E6259";
const LABEL_COLOR = "#2A4640";

const CATEGORY_COLORS = {
  ms: "#3E6259",     // manuscripts — same teal as before, so pure-Ms
                      // clusters look unchanged from the prior version
  ts: "#B08D57",      // typescripts — warm amber, clearly distinct
  mixed: "#6B5B95",   // both categories present in one cluster
  unknown: "#8A8877", // title didn't match either prefix (shouldn't
                      // normally happen, but fails safely rather than
                      // crashing)
};

function categoryOf(title) {
  if (/^Ts-/i.test(title)) return "ts";
  if (/^Ms-/i.test(title)) return "ms";
  return "unknown";
}

function clusterColor(items) {
  const cats = new Set(items.map((d) => categoryOf(d.title)));
  return cats.size === 1 ? CATEGORY_COLORS[[...cats][0]] : CATEGORY_COLORS.mixed;
}

const MARGIN = { top: 30, right: 30, bottom: 26, left: 30 };
const HEIGHT = 520;
const AXIS_GUTTER = 40;
const OVERVIEW_HEIGHT = 46;
const OVERVIEW_MARGIN_TOP = 14;
const CLUSTER_PX = 5;
const MARKER_PAD = 3;
const CLIP_PAD_X = 70;
const CLIP_PAD_Y = 90;

const card = document.getElementById("card");
const tooltipEl = document.getElementById("tooltip");
const svg = d3.select("#chart");

const LEGEND_LABELS = {
  ms: "Manuscript (Ms)",
  ts: "Typescript (Ts)",
  mixed: "Mixed Ms/Ts",
};
const legendEl = document.getElementById("legend");
if (legendEl) {
  Object.entries(LEGEND_LABELS).forEach(([key, label]) => {
    const item = document.createElement("div");
    item.className = "legend-item";
    item.innerHTML = `<span class="legend-dot" style="background:${CATEGORY_COLORS[key]}"></span><span class="legend-label">${label}</span>`;
    legendEl.appendChild(item);
  });
}

const nExact = DATA.filter((d) => !d.isRange).length;
const nRange = DATA.length - nExact;

const filtersEl = document.createElement("div");
filtersEl.style.cssText =
  "display:flex;align-items:center;flex-wrap:wrap;gap:6px 18px;margin:0 0 6px;" +
  "font:12px system-ui,sans-serif;color:#5F5E5A;";

function makeFilterBox(key, shapeCss, label, count) {
  const wrap = document.createElement("label");
  wrap.style.cssText = "display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none;";

  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = true;
  box.style.cssText = "margin:0;cursor:pointer;accent-color:#3E6259;";
  wrap.appendChild(box);

  const shape = document.createElement("span");
  shape.style.cssText = `width:8px;height:8px;display:inline-block;background:#8A8877;${shapeCss}`;
  wrap.appendChild(shape);

  const text = document.createElement("span");
  text.innerHTML = `${label} <span style="opacity:.6">(${count.toLocaleString()})</span>`;
  wrap.appendChild(text);

  box.addEventListener("change", () => {
    filterState[key] = box.checked;
    // Never let both be off: there'd be nothing left to show.
    if (!filterState.exact && !filterState.range) {
      filterState[key] = true;
      box.checked = true;
      return;
    }
    applyFilter();
    onFilterChange();
  });
  return wrap;
}

filtersEl.appendChild(makeFilterBox("exact", "border-radius:50%;", "Exact date", nExact));
filtersEl.appendChild(makeFilterBox("range", "transform:rotate(45deg) scale(0.9);", "Estimated date (diamond + range bar)", nRange));

const chartEl = document.getElementById("chart");
if (chartEl && chartEl.parentNode === card) card.insertBefore(filtersEl, chartEl);

// ---- date formatting for exact vs. estimated entries ----
const fmtDayYear = d3.timeFormat("%b %-d, %Y");
const fmtDay = d3.timeFormat("%b %-d");
const fmtMonthYear = d3.timeFormat("%b %Y");
const fmtMonth = d3.timeFormat("%b");

function isFirstOfMonth(d) { return d.getDate() === 1; }
function isLastOfMonth(d) {
  const next = new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1);
  return next.getDate() === 1;
}

function formatEntryDate(d) {
  if (!d.isRange) return fmtDayYear(d.date);
  const s = d.date, e = d.endDate;
  const sameYear = s.getFullYear() === e.getFullYear();

  if (isFirstOfMonth(s) && isLastOfMonth(e)) {
    if (sameYear && s.getMonth() === 0 && e.getMonth() === 11) return `${s.getFullYear()}`;
    if (sameYear && s.getMonth() === e.getMonth()) return fmtMonthYear(s);
    return sameYear
      ? `${fmtMonth(s)} \u2013 ${fmtMonth(e)} ${s.getFullYear()}`
      : `${fmtMonthYear(s)} \u2013 ${fmtMonthYear(e)}`;
  }
  return sameYear
    ? `${fmtDay(s)} \u2013 ${fmtDayYear(e)}`
    : `${fmtDayYear(s)} \u2013 ${fmtDayYear(e)}`;
}

function computeLabelLines(text, maxCharsPerLine) {
  const words = text.split(/\s+/);
  const lines = [];
  let current = "";
  words.forEach((word) => {
    const test = current ? current + " " + word : word;
    if (test.length > maxCharsPerLine && current) {
      lines.push(current);
      current = word;
    } else {
      current = test;
    }
  });
  if (current) lines.push(current);
  return lines;
}

function applyLabelLines(textSel, lines, lineHeight, baseY, up) {
  textSel.selectAll("tspan").remove();
  const n = lines.length;
  lines.forEach((line, i) => {
    // "up" labels grow upward from the stem, so the LAST line sits at
    // baseY and earlier lines stack above it; "down" labels grow
    // downward, so the FIRST line sits at baseY.
    const y = up ? baseY - (n - 1 - i) * lineHeight : baseY + i * lineHeight;
    textSel.append("tspan").attr("x", 0).attr("y", y).text(line);
  });
}

const LABEL_FONT = "11.5px Georgia, 'Iowan Old Style', serif";
const measureCanvas = document.createElement("canvas");
const measureCtx = measureCanvas.getContext("2d");
function measureLabelWidth(lines) {
  measureCtx.font = LABEL_FONT;
  let maxW = 0;
  lines.forEach((line) => {
    const w = measureCtx.measureText(line).width;
    if (w > maxW) maxW = w;
  });
  return maxW;
}

let width = card.clientWidth - 36;
let innerWidth = Math.max(width - MARGIN.left - MARGIN.right, 100);
let innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;

function linearX(zx) {
  const [d0, d1] = zx.domain();
  const [r0, r1] = zx.range();
  const t0 = d0.getTime();
  const k = (r1 - r0) / (d1.getTime() - t0);
  return (t) => r0 + (t - t0) * k;
}

function markerRadius(count, isRange) {
  return count > 1 ? Math.min(6 + Math.sqrt(count) * 2, 15) : (isRange ? 7 : 5);
}

function groupRanges(list, toX) {
  const groups = [];
  let cur = null;
  for (let i = 0; i < list.length; i++) {
    const x = toX(list[i].t);
    if (cur && x - cur.lastX <= CLUSTER_PX) {
      cur.hi = i + 1;
      cur.lastX = x;
      cur.sumX += x;
    } else {
      cur = { lo: i, hi: i + 1, lastX: x, sumX: x };
      groups.push(cur);
    }
  }
  for (const g of groups) g.x = g.sumX / (g.hi - g.lo);

  const radius = (g) => markerRadius(g.hi - g.lo, list[g.lo].isRange);
  const out = [];
  for (let g of groups) {
    while (out.length) {
      const prev = out[out.length - 1];
      if (g.x - prev.x >= radius(prev) + radius(g) + MARKER_PAD) break;
      const sumX = prev.sumX + g.sumX;
      g = { lo: prev.lo, hi: g.hi, sumX, x: sumX / (g.hi - prev.lo) };
      out.pop();
    }
    out.push(g);
  }
  return out;
}

function clusterPoints(zx) {
  const grouped = groupRanges(activeData, linearX(zx)).map((g) => ({
    x: g.x,
    items: activeData.slice(g.lo, g.hi),
  }));

  const currentK = currentTransform.k;
  const [, kMax] = zoomBehavior.scaleExtent();
  return explodeAtMaxZoom(grouped, currentK, kMax);
}

const FAN_SPACING = 14; // px between fanned-out items, once even max zoom can't separate them by real time

function explodeAtMaxZoom(clusters, currentK, kMax) {
  if (currentK < kMax) return clusters;
  const result = [];
  clusters.forEach((c) => {
    if (c.items.length === 1) {
      result.push(c);
      return;
    }
    const n = c.items.length;
    const totalWidth = (n - 1) * FAN_SPACING;
    const startX = c.x - totalWidth / 2;
    c.items.forEach((item, i) => {
      result.push({ x: startX + i * FAN_SPACING, items: [item] });
    });
  });
  return result;
}

function annotateClusterYears(clusters) {
  clusters.forEach((c) => {
    let minT = Infinity, maxT = -Infinity;
    for (const d of c.items) {
      const s = d.date.getTime();
      const e = d.endDate ? d.endDate.getTime() : s;
      if (s < minT) minT = s;
      if (e > maxT) maxT = e;
    }
    c.displayStartYear = new Date(minT).getFullYear();
    c.displayEndYear = new Date(maxT).getFullYear();
  });
}

let zoomBehavior, brush, brushSel, xScale, currentXScale;
let suppressBrush = false;
let suppressZoom = false;

let onFilterChange = () => {};

let currentTransform = d3.zoomIdentity;
let targetTransform = d3.zoomIdentity;

function build() {
  currentTransform = d3.zoomIdentity;
  targetTransform = d3.zoomIdentity;
  svg.selectAll("*").remove();
  svg
    .attr("width", width)
    .attr("height", HEIGHT + OVERVIEW_MARGIN_TOP + OVERVIEW_HEIGHT)
    .style("font-family", "Georgia, 'Iowan Old Style', serif");

  const domainMin = d3.min(DATA, d => Math.min(d.plotDate.getTime(), d.date.getTime()));
  const domainMax = d3.max(DATA, d => d.endDate
    ? Math.max(d.plotDate.getTime(), d.endDate.getTime())
    : d.plotDate.getTime());
  const DOMAIN_PAD = 0.03;
  const domainSpan = domainMax - domainMin;
  xScale = d3.scaleTime()
    .domain([new Date(domainMin - domainSpan * DOMAIN_PAD), new Date(domainMax + domainSpan * DOMAIN_PAD)])
    .range([0, innerWidth]);
  currentXScale = xScale;

  const defs = svg.append("defs");
  defs.append("clipPath").attr("id", "plot-clip")
    .append("rect")
    .attr("x", -CLIP_PAD_X)
    .attr("y", -CLIP_PAD_Y)
    .attr("width", innerWidth + CLIP_PAD_X * 2)
    .attr("height", innerHeight + CLIP_PAD_Y * 2);

  const main = svg.append("g").attr("transform", `translate(${MARGIN.left},${MARGIN.top})`);
  const baselineY = innerHeight - AXIS_GUTTER;

  main.append("line")
    .attr("x1", -CLIP_PAD_X).attr("x2", innerWidth + CLIP_PAD_X)
    .attr("y1", baselineY).attr("y2", baselineY)
    .attr("stroke", "#C9CDD1").attr("stroke-width", 1);

  const axisG = main.append("g").attr("class", "x-axis")
    .attr("transform", `translate(0,${baselineY})`);

  const plot = main.append("g").attr("clip-path", "url(#plot-clip)");
  const markersG = plot.append("g").attr("class", "markers");

  function renderAxis(zx) {
    const span = zx.domain()[1] - zx.domain()[0];
    const years = span / (1000 * 60 * 60 * 24 * 365);
    let ticks, fmt;
    if (years > 60) { ticks = d3.timeYear.every(10); fmt = d3.timeFormat("%Y"); }
    else if (years > 25) { ticks = d3.timeYear.every(5); fmt = d3.timeFormat("%Y"); }
    else if (years > 8) { ticks = d3.timeYear.every(2); fmt = d3.timeFormat("%Y"); }
    else if (years > 2) { ticks = d3.timeYear.every(1); fmt = d3.timeFormat("%Y"); }
    else if (years > 0.5) { ticks = d3.timeMonth.every(3); fmt = d3.timeFormat("%b %Y"); }
    else if (years > 0.15) { ticks = d3.timeMonth.every(1); fmt = d3.timeFormat("%b %Y"); }
    else if (years > 0.04) { ticks = d3.timeWeek.every(1); fmt = d3.timeFormat("%b %e"); }
    else { ticks = d3.timeDay.every(1); fmt = d3.timeFormat("%b %e"); }  // days are the finest unit: no hours/minutes

    axisG.call(d3.axisBottom(zx).ticks(ticks).tickFormat(fmt).tickSizeOuter(0))
      .call(g => g.select(".domain").remove())
      .call(g => g.selectAll(".tick line").attr("stroke", "#C9CDD1"))
      .call(g => g.selectAll(".tick text").attr("fill", "#3D4145").attr("font-size", 12));

    if (axisG.selectAll(".tick").empty()) {
      const mid = new Date((zx.domain()[0].getTime() + zx.domain()[1].getTime()) / 2);
      const g = axisG.append("g").attr("class", "tick")
        .attr("transform", `translate(${zx(mid)},0)`);
      g.append("line").attr("y2", 6).attr("stroke", "#C9CDD1");
      g.append("text").attr("y", 9).attr("dy", "0.71em")
        .attr("text-anchor", "middle").attr("fill", "#3D4145").attr("font-size", 12)
        .text(d3.timeFormat("%b %e, %Y")(mid));
    }
  }

  function renderMarkers(zx) {
    const baselineY = innerHeight - AXIS_GUTTER;
    const allClusters = clusterPoints(zx);

    const heightScale = computeHeightScale(allClusters);

    const toX = linearX(zx);
    const viewLeft = -CLIP_PAD_X - 20;
    const viewRight = innerWidth + CLIP_PAD_X + 20;
    const clusters = allClusters.filter((c) => {
      if (c.x >= viewLeft && c.x <= viewRight) return true;
      if (c.items.length === 1 && c.items[0].isRange) {
        const d = c.items[0];
        return toX(d.endDate.getTime()) >= viewLeft && toX(d.date.getTime()) <= viewRight;
      }
      return false;
    });
    annotateClusterYears(clusters);

    tooltipEl.style.display = "none";
    markersG.selectAll("*").remove();

    const groups = markersG
      .selectAll("g.marker")
      .data(clusters)
      .enter()
      .append("g")
      .attr("class", "marker")
      .style("cursor", "pointer")
      .on("mouseenter", function (event, c) {
        d3.select(this).raise();
        showTooltip(c, event);
      })
      .on("mousemove", function (event) {
        positionTooltip(event);
      })
      .on("mouseleave", function () {
        tooltipEl.style.display = "none";
      })
      .on("click", function (event, c) {
        if (c.items.length > 1) {
          zoomToCluster(c);
        } else if (c.items[0].link) {
          window.open(c.items[0].link, "_blank", "noopener");
        }
      });

    groups.append("line").attr("class", "rangebar");
    groups.append("line").attr("class", "stem").attr("stroke-width", 1.5);
    groups
      .append("circle")
      .attr("class", "dot")
      .attr("stroke", "#FBFAF6")
      .attr("stroke-width", 1.5);
    groups
      .append("path")
      .attr("class", "diamond")
      .attr("stroke", "#FBFAF6")
      .attr("stroke-width", 1.5);
    groups.append("text").attr("class", "label").attr("font-size", 11.5);
    groups
      .append("text")
      .attr("class", "count")
      .attr("font-size", 9)
      .attr("font-family", "system-ui, sans-serif")
      .attr("text-anchor", "middle")
      .attr("fill", "#FBFAF6");

    const LABEL_PAD = 8;
    let lastLabelRight = -Infinity;

    groups.each(function (c, idx) {
      const isCluster = c.items.length > 1;
      const stemLen = heightScale(c.items.length);
      const y2 = baselineY - stemLen;
      const r = isCluster ? markerRadius(c.items.length, false) : 5;
      const color = clusterColor(c.items);

      const single = !isCluster ? c.items[0] : null;
      const isRangeMarker = !!(single && single.isRange);

      const g = d3.select(this);
      g.attr("transform", `translate(${c.x},0)`);
      g.style("cursor", isCluster ? "zoom-in" : "pointer");

      const bar = g.select("line.rangebar");
      if (isRangeMarker) {
        let bl = toX(single.date.getTime()) - c.x;
        let br = toX(single.endDate.getTime()) - c.x;
        if (br - bl < 3) {               // keep a very short range visible
          const m = (bl + br) / 2;
          bl = m - 1.5;
          br = m + 1.5;
        }
        bar.attr("x1", bl).attr("x2", br)
          .attr("y1", baselineY - 3).attr("y2", baselineY - 3)
          .attr("stroke", color).attr("stroke-width", 5).attr("opacity", 0.45);
      } else {
        bar.attr("opacity", 0);
      }

      g.select("line.stem")
        .attr("x1", 0).attr("x2", 0).attr("y1", baselineY).attr("y2", y2)
        .attr("stroke", color).attr("opacity", 0.55);
      g.select("circle.dot")
        .attr("cy", y2).attr("r", r)
        .attr("fill", color).attr("opacity", isRangeMarker ? 0 : 1);
      const rd = 7; // half-diagonal; a touch larger than the circle radius so it reads as the same weight
      g.select("path.diamond")
        .attr("d", `M0,${y2 - rd}L${rd},${y2}L0,${y2 + rd}L${-rd},${y2}Z`)
        .attr("fill", color).attr("opacity", isRangeMarker ? 1 : 0);
      g.select("text.count")
        .attr("y", y2 + 3)
        .attr("opacity", isCluster ? 1 : 0)
        .text(isCluster ? c.items.length : "");

      const labelSel = g.select("text.label")
        .attr("text-anchor", "middle")
        .attr("fill", LABEL_COLOR);

      if (isCluster) {
        labelSel.selectAll("tspan").remove();
        labelSel.attr("opacity", 0);
        return;
      }

      const lines = computeLabelLines(c.items[0].title, 16);
      const measuredWidth = measureLabelWidth(lines);
      const left = c.x - measuredWidth / 2;
      const right = c.x + measuredWidth / 2;
      const showLabel = left > lastLabelRight + LABEL_PAD;

      if (showLabel) {
        applyLabelLines(labelSel, lines, 13, y2 - (isRangeMarker ? 12 : 10), true);
        labelSel.attr("opacity", 1);
        lastLabelRight = right;
      } else {
        labelSel.selectAll("tspan").remove();
        labelSel.attr("opacity", 0);
      }
    });

    markersG.raise();
  }

  function zoomToCluster(c) {
    const items = c.items;
    const t0 = items[0].t;
    const t1 = items[items.length - 1].t;
    const [kMin, kMax] = zoomBehavior.scaleExtent();

    let lo = 0, hi = activeData.length;
    while (lo < hi) {
      const m = (lo + hi) >> 1;
      if (activeData[m].t < t0) lo = m + 1; else hi = m;
    }
    while (lo < activeData.length && activeData[lo] !== items[0]) lo++; // identical timestamps
    const found = lo < activeData.length;
    const prev = found ? activeData[lo - 1] : undefined;
    const next = found ? activeData[lo + items.length] : undefined;

    const span = t1 > t0 ? t1 - t0 : 1000 * 60 * 60 * 24;
    const edge = span * 0.03;
    const from = t0 - (prev ? Math.min(edge, (t0 - prev.t) / 2) : edge);
    const to = t1 + (next ? Math.min(edge, (next.t - t1) / 2) : edge);

    const x0 = xScale(new Date(from));
    const x1 = xScale(new Date(to));
    const fitK = innerWidth / (x1 - x0);

    const toX1 = linearX(xScale); // time -> pixel at zoom 1
    const splits = (z) => {
      const parts = groupRanges(items, (t) => toX1(t) * z);
      return parts.length >= 2 && Math.max(...parts.map((q) => q.hi - q.lo)) < items.length * 0.8;
    };

    let k = fitK, centerT = (from + to) / 2;
    if (!splits(k)) {
      let lo = k, hi = k * 1.5;
      while (!splits(hi) && hi < kMax) { lo = hi; hi *= 1.5; }
      hi = Math.min(hi, kMax);
      for (let i = 0; i < 12; i++) {
        const mid = (lo + hi) / 2;
        if (splits(mid)) hi = mid; else lo = mid;
      }
      k = hi;
      let maxGap = 0;
      centerT = (t0 + t1) / 2;
      for (let i = 1; i < items.length; i++) {
        const g = items[i].t - items[i - 1].t;
        if (g > maxGap) { maxGap = g; centerT = (items[i].t + items[i - 1].t) / 2; }
      }
    }
    k = Math.min(Math.max(k, kMin), kMax);

    const tx = innerWidth / 2 - xScale(new Date(centerT)) * k;
    const transform = d3.zoomIdentity.translate(tx, 0).scale(k);

    targetTransform = transform;
    svg.interrupt();
    svg.transition().duration(500).call(zoomBehavior.transform, transform);
  }

  function showTooltip(c, event) {
    const items = c.items.length === 1
      ? c.items
      : c.items.slice().sort((a, b) => a.date - b.date);
    if (items.length === 1) {
      const d = items[0];
      const note = d.isRange ? `<div style="opacity:.7;font-size:11px">estimated date</div>` : "";
      tooltipEl.innerHTML = `<div class="tt-date">${formatEntryDate(d)}</div>${note}<div>${d.title}</div>`;
    } else {
      const range =
        c.displayStartYear === c.displayEndYear
          ? `${c.displayStartYear}`
          : `${c.displayStartYear}\u2013${c.displayEndYear}`;
      const preview = items
        .slice(0, 5)
        .map((d) => `${formatEntryDate(d)}${d.isRange ? " (est.)" : ""}: ${d.title}`)
        .join("<br/>");
      const more = items.length > 5 ? `<br/>+${items.length - 5} more` : "";
      tooltipEl.innerHTML = `<div class="tt-date">${range} \u00b7 ${items.length} entries</div><div>${preview}${more}</div>`;
    }
    tooltipEl.style.display = "block";
    positionTooltip(event);
  }

  function positionTooltip(event) {
    const cardRect = card.getBoundingClientRect();
    let left = event.clientX - cardRect.left + 14;
    let top = event.clientY - cardRect.top - 40;
    left = Math.min(Math.max(left, 6), cardRect.width - 210);
    tooltipEl.style.left = left + "px";
    tooltipEl.style.top = top + "px";
  }

  zoomBehavior = d3.zoom()
    .scaleExtent([1, 200000])
    .translateExtent([[0, 0], [innerWidth, innerHeight]])
    .extent([[0, 0], [innerWidth, innerHeight]])
    .interpolate(d3.interpolate) // straight line from start to end scale — the
    .on("zoom", zoomed);

  main.call(zoomBehavior);

  renderAxis(xScale);
  renderMarkers(xScale);

  let pendingZx = null;
  let renderScheduled = false;
  function scheduleFullRender(zx) {
    pendingZx = zx;
    if (!renderScheduled) {
      renderScheduled = true;
      requestAnimationFrame(() => {
        renderScheduled = false;
        renderAxis(pendingZx);
        renderMarkers(pendingZx);
      });
    }
  }

  function zoomed(event) {
    currentTransform = event.transform;
    if (event.sourceEvent) targetTransform = event.transform;
    const zx = event.transform.rescaleX(xScale);
    currentXScale = zx;
    scheduleFullRender(zx);

    if (!suppressZoom) {
      let [x0, x1] = zx.range().map(r => xScale(zx.invert(r)));
      const MIN_BRUSH_PX = 6;
      if (x1 - x0 < MIN_BRUSH_PX) {
        const mid = (x0 + x1) / 2;
        x0 = mid - MIN_BRUSH_PX / 2;
        x1 = mid + MIN_BRUSH_PX / 2;
      }
      suppressBrush = true;
      brushSel.call(brush.move, [x0, x1]);
      suppressBrush = false;
    }
  }

  const overviewG = svg.append("g")
    .attr("transform", `translate(${MARGIN.left},${HEIGHT + OVERVIEW_MARGIN_TOP})`);

  overviewG.append("rect")
    .attr("width", innerWidth).attr("height", OVERVIEW_HEIGHT)
    .attr("fill", "#F1EFE8").attr("rx", 4);

  const ticksG = overviewG.append("g").attr("class", "ticks");

  function drawOverviewTicks() {
    ticksG.selectAll("*").remove();
    const bins = new Map(); // pixel column -> { n, ms, ts }
    activeData.forEach((d) => {
      const px = Math.max(0, Math.min(innerWidth - 1, Math.floor(xScale(d.plotDate))));
      let b = bins.get(px);
      if (!b) { b = { n: 0, ms: 0, ts: 0 }; bins.set(px, b); }
      b.n++;
      if (categoryOf(d.title) === "ts") b.ts++; else b.ms++;
    });
    const maxBin = d3.max(Array.from(bins.values()), (b) => b.n) || 1;

    ticksG.selectAll("rect.tick")
      .data(Array.from(bins.entries()))
      .enter().append("rect")
      .attr("class", "tick")
      .attr("x", ([px]) => px)
      .attr("width", 1)
      .attr("y", 4)
      .attr("height", OVERVIEW_HEIGHT - 8)
      .attr("fill", ([, b]) =>
        b.ts && b.ms ? CATEGORY_COLORS.mixed : b.ts ? CATEGORY_COLORS.ts : CATEGORY_COLORS.ms)
      .attr("opacity", ([, b]) => 0.25 + 0.75 * Math.log1p(b.n) / Math.log1p(maxBin));
  }
  drawOverviewTicks();

  onFilterChange = () => {
    drawOverviewTicks();
    renderMarkers(currentXScale);
  };

  brush = d3.brushX()
    .extent([[0, 0], [innerWidth, OVERVIEW_HEIGHT]])
    .on("brush end", brushed);

  brushSel = overviewG.append("g").attr("class", "brush").call(brush);
  brushSel.call(brush.move, xScale.range());
  brushSel.selectAll(".selection").attr("fill", "#3E6259").attr("fill-opacity", 0.12).attr("stroke", "#3E6259");
  brushSel.selectAll(".handle").attr("fill", "#3E6259");

  function brushed(event) {
    if (!event.selection || suppressBrush) return;
    const [x0, x1] = event.selection;
    const newDomain = [xScale.invert(x0), xScale.invert(x1)];
    const k = innerWidth / (xScale(newDomain[1]) - xScale(newDomain[0]));
    const tx = -xScale(newDomain[0]) * k;
    const transform = d3.zoomIdentity.scale(k).translate(tx / k, 0);

    targetTransform = transform;
    suppressZoom = true;
    svg.interrupt();
    svg.call(zoomBehavior.transform, transform);
    suppressZoom = false;
  }

  function scaleAroundCenter(factor) {
    const oldK = targetTransform.k;
    const oldX = targetTransform.x;
    const [kMin, kMax] = zoomBehavior.scaleExtent();
    const newK = Math.min(Math.max(oldK * factor, kMin), kMax);
    const centerDataX = (innerWidth / 2 - oldX) / oldK;
    const newX = innerWidth / 2 - centerDataX * newK;
    return d3.zoomIdentity.translate(newX, 0).scale(newK);
  }

  document.getElementById("zoom-in").onclick = () => {
    const transform = scaleAroundCenter(1.6);
    targetTransform = transform;
    svg.interrupt();
    svg.transition().duration(300).call(zoomBehavior.transform, transform);
  };
  document.getElementById("zoom-out").onclick = () => {
    const transform = scaleAroundCenter(1 / 1.6);
    targetTransform = transform;
    svg.interrupt();
    svg.transition().duration(300).call(zoomBehavior.transform, transform);
  };
  document.getElementById("reset-btn").onclick = () => {
    targetTransform = d3.zoomIdentity;
    svg.interrupt();
    svg.transition().duration(400).call(zoomBehavior.transform, d3.zoomIdentity);
  };
}

build();

window.addEventListener("resize", () => {
  width = card.clientWidth - 36;
  innerWidth = Math.max(width - MARGIN.left - MARGIN.right, 100);
  build();
});
"""
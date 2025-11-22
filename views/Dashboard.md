# Daily totals and flow
```dataview
TABLE
  date,
  sum(tu) AS "Total TU",
  length(rows) AS "Sessions",
  any(flow) AS "Flow"
FROM "Logs/TaskUnits"
WHERE date
GROUP BY date
SORT date DESC
```

# Weekly summary
```dataview
TABLE
  dateweek(date) AS "Week",
  sum(tu) AS "Total TU",
  round(sum(tu) / length(groupby(date)), 1) AS "Avg TU per day"
FROM "Logs/TaskUnits"
WHERE date
GROUP BY dateweek(date)
SORT "Week" DESC
```

# Activity breakdown
```dataview
TABLE
  activity,
  sum(tu) AS "Total TU",
  length(rows) AS "Sessions"
FROM "Logs/TaskUnits"
WHERE activity
GROUP BY activity
SORT sum(tu) DESC
```
# OHER statistics and review
```dataview
TABLE
  date,
  activity,
  observation,
  hypothesis,
  experiment,
  result,
  tu
FROM "Logs/TaskUnits"
WHERE oher = true
SORT date DESC
```

# Flow vs Task Units (table)
```dataview
TABLE
  date,
  any(flow) AS "Flow",
  sum(tu) AS "Total TU",
  length(rows) AS "Sessions"
FROM "Logs/TaskUnits"
WHERE date
GROUP BY date
SORT date DESC
```

# Bar Chart
```dataviewjs
const pages = dv.pages('"Logs/TaskUnits"')
  .where(p => p.date)
  .groupBy(p => p.date)
  .sort(g => g.key, 'asc');

dv.table(
  ["Date", "Flow", "Total TU", "Bar"],
  pages.map(g => {
    const flow = g.rows[0].flow ?? 0;
    const totalTU = g.rows.map(r => r.tu ?? 0).reduce((a, b) => a + b, 0);
    const bar = "█".repeat(Math.max(1, Math.round(totalTU)));
    return [g.key, flow, totalTU, bar];
  })
);
```



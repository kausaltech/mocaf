cube(`DailyLengths`, {
  sql: `SELECT * FROM public.analytics_dailymodesummary`,
  preAggregations: {
  },
  joins: {
    Areas: {
      relationship: `belongsTo`,
      sql: `${CUBE}.area_id = ${Areas}.id`,
    },
    TransportModes: {
      relationship: `belongsTo`,
      sql: `${CUBE}.mode_id = ${TransportModes}.id`,
    }
  },
  measures: {
    totalLength: {
      sql: `length`,
      type: `sum`,
    },
  },
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    date: {
      sql: `date`,
      type: `time`
    },
    areaId: {
      sql: `area_id`,
      type: `number`,
    },
    modeId: {
      sql: `mode_id`,
      type: `number`,
    },
  },
  segments: {
    weekends: {
      sql: `EXTRACT(ISODOW FROM ${CUBE}.date) IN (6, 7)`
    },
    weekdays: {
      sql: `EXTRACT(ISODOW FROM ${CUBE}.date) NOT IN (6, 7)`
    },
  },
  dataSource: `default`
});

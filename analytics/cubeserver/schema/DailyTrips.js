cube(`DailyTrips`, {
  sql: `SELECT * FROM public.analytics_dailytripsummary`,
  preAggregations: {
  },
  joins: {
    TransportModes: {
      relationship: `belongsTo`,
      sql: `${CUBE}.mode_id = ${TransportModes}.id`,
    }
  },
  measures: {
    totalTrips: {
      sql: `trips`,
      type: `sum`,
    },
  },
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    modeId: {
      sql: `mode_id`,
      type: 'number',
    },
    modeSpecifier: {
      sql: `mode_specifier`,
      type: `string`
    },
    originId: {
      sql: `origin_id`,
      type: 'number',
    },
    destId: {
      sql: `dest_id`,
      type: 'number',
    },
    date: {
      sql: `date`,
      type: `time`
    }
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

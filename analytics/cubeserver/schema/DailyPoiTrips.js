cube(`DailyPoiTrips`, {
  sql: `SELECT * FROM public.analytics_dailypoitripsummary`,
  preAggregations: {
  },
  joins: {
    TransportModes: {
      relationship: `belongsTo`,
      sql: `${CUBE}.mode_id = ${TransportModes}.id`,
    },
    Pois: {
      relationship: `belongsTo`,
      sql: `${CUBE}.poi_id = ${Pois}.id`,
    },
    Areas: {
      relationship: `belongsTo`,
      sql: `${CUBE}.area_id = ${Areas}.id`,
    }
  },
  measures: {
    totalTrips: {
      sql: `trips`,
      type: `sum`,
    },
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
    isInbound: {
      sql: `is_inbound`,
      type: `boolean`,
    },
    modeId: {
      sql: `mode_id`,
      type: 'number',
    },
    modeSpecifier: {
      sql: `mode_specifier`,
      type: `string`
    },
    poiId: {
      sql: `poi_id`,
      type: 'number',
    },
    areaId: {
      sql: `area_id`,
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

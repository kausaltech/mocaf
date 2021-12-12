cube(`Areas`, {
  sql: `SELECT * FROM public.analytics_area`,
  preAggregations: {
    // Pre-Aggregations definitions go here
    // Learn more here: https://cube.dev/docs/caching/pre-aggregations/getting-started  
  },
  joins: {
    AreaTypes: {
      relationship: `belongsTo`,
      sql: `${CUBE}.type_id = ${AreaTypes}.id`,
    },
  },
  measures: {
    count: {
      type: `count`,
      drillMembers: [id, identifier, name]
    }
  },
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    identifier: {
      sql: `identifier`,
      type: `string`
    },
    name: {
      sql: `name`,
      type: `string`
    },
    typeId: {
      sql: `type_id`,
      type: `number`,
    },
  },
  dataSource: `default`
});

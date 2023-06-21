cube(`TransportModes`, {
  sql: `SELECT * FROM public.trips_transportmode`,
  preAggregations: {
    // Pre-Aggregations definitions go here
    // Learn more here: https://cube.dev/docs/caching/pre-aggregations/getting-started  
  },
  joins: {
    
  },
  measures: {
    count: {
      type: `count`,
      drillMembers: [id, name, identifier]
    }
  },
  dimensions: {
    id: {
      sql: `id`,
      type: `number`,
      primaryKey: true
    },
    name: {
      sql: `name`,
      type: `string`
    },
    identifier: {
      sql: `identifier`,
      type: `string`
    }
  },
  dataSource: `default`
});

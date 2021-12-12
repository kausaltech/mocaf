cube(`AreaTypes`, {
  sql: `SELECT * FROM public.analytics_areatype`,
  
  preAggregations: {
    // Pre-Aggregations definitions go here
    // Learn more here: https://cube.dev/docs/caching/pre-aggregations/getting-started  
  },
  
  joins: {
    
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
  },
  dataSource: `default`
});

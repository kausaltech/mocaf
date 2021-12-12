const CubejsServer = require('@cubejs-backend/server');

const options = {
  dbType: 'postgres',
  apiSecret: 'a',
  checkAuth: (req, auth) => { 
    req.securityContext = {}
  },
  telemetry: false,
};
const server = new CubejsServer(options);

server.listen().then(({ version, port }) => {
  console.log(`🚀 Cube.js server (${version}) is listening on ${port}`);
});

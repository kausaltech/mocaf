const esbuild = require('esbuild');
const path = require('path');
const { program } = require('commander');
const { resolveToEsbuildTarget } = require('esbuild-plugin-browserslist');
const browserslist = require('browserslist');

require('dotenv').config()

const ANALYTICS_STATIC_DIR = `${__dirname}/../static/analytics`;

const TARGETS = [
  {
    entryPoints: ['src/main.js'],
    outfile: `${ANALYTICS_STATIC_DIR}/main.js`,
  },
]

const TARGET_BROWSERS = resolveToEsbuildTarget(browserslist(), {
  printUnknownTargets: false,
});

const BUILD_OPTS = {
  bundle: true,
  //target: TARGET_BROWSERS,
  target: ['es2020'],
  loader: {
    '.js': 'tsx',
  },
  color: process.env.COLOR === "false" ? false : true,
  logLevel: 'info',
  sourcemap: true,
  define: {
    'MAPBOX_ACCESS_TOKEN': `"${process.env.MAPBOX_ACCESS_TOKEN}"`,
  }
}

async function doBuild(isProd, opts) {
  console.log(`Generating ${isProd ? 'production' : 'development'} build`);
  for (const target of TARGETS) {
    console.log(`Building ${target.entryPoints.join(', ')}`);
    console.log(`  Output to: ${path.relative(__dirname, target.outfile)}`);
    const buildOpts = {
      ...BUILD_OPTS,
      ...target,
      define: {
        'process.env.NODE_ENV': isProd ? "'production'" : "'development'",
        ...BUILD_OPTS.define,
      },
      metafile: true,
    };
    if (isProd) {
      buildOpts.sourcemap = true;
      buildOpts.minify = true;
    }
    if (opts.watch) {
      buildOpts.watch = true;
    }
    const res = await esbuild.build(buildOpts);
    if (opts.verbose) {
      console.log(await esbuild.analyzeMetafile(res.metafile));
    }
  }
}


program.version('0.0.1');
program.option('-w, --watch', 'watch files for changes and rebuild')
program.option('-v, --verbose', 'increase verbosity')
program.parse(process.argv);

const opts = program.opts();
doBuild(opts.watch ? false : true, opts).catch(() => process.exit(1));

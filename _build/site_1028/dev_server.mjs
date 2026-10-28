// Local smoke server only. Preview HTML keeps its intended remote URLs.
import { createServer } from 'vite';
import consolePipe from 'vite-plugin-console-pipe';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const home = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(home, 'build');
// Upstream 2.1.0 injects a relative client URL; make it absolute for /redlines/.
const pipe = consolePipe();
const injectPipe = pipe.transformIndexHtml;
pipe.transformIndexHtml = html => {
  const result = injectPipe(html);
  for (const tag of result.tags || []) {
    if (tag.attrs?.src === '@console-pipe/client') tag.attrs.src = '/@console-pipe/client';
  }
  return result;
};
const server = await createServer({
  configFile: false,
  root: path.join(home, 'preview'),
  publicDir: false,
  cacheDir: path.join(home, '.vite'),
  plugins: [pipe, {
    name: 'local-review-assets',
    transformIndexHtml(html) {
      return html.replace(/https:\/\/pub-92c80eda1059428394970066c8500eda\.r2\.dev\/(d2p_v1|redlines_0929ar|wordcraft1014)\//g, '/__assets/$1/');
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === '/__health') {
          res.setHeader('Content-Type', 'application/json'); res.end('{"ok":true}'); return;
        }
        if (!req.url.startsWith('/__assets/')) return next();
        const rel = decodeURIComponent(req.url.split('?')[0].slice('/__assets/'.length));
        const file = path.resolve(build, rel);
        if (!file.startsWith(build + path.sep) || !fs.existsSync(file)) { res.statusCode=404; res.end(); return; }
        res.setHeader('Access-Control-Allow-Origin','*');
        res.setHeader('Content-Type', file.endsWith('.webp') ? 'image/webp' : 'application/pdf');
        fs.createReadStream(file).pipe(res);
      });
    }
  }],
  server: { host: '127.0.0.1', port: 8178, strictPort: true, fs: { allow: [home] } }
});
await server.listen();
console.log('Review smoke server: http://127.0.0.1:8178; vite-plugin-console-pipe active');

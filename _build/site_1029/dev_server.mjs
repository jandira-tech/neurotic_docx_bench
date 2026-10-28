// Local preview only; saved HTML retains its intended R2 URLs.
import { createServer } from 'vite';
import consolePipe from 'vite-plugin-console-pipe';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const home = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(home, 'build');
const prior = path.resolve(home, '../site_1028/build');
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
  configFile: false, root: path.join(home, 'preview'), publicDir: false,
  cacheDir: path.join(home, '.vite'),
  plugins: [pipe, {
    name: 'local-review-assets',
    transformIndexHtml(html) {
      return html.replace(/https:\/\/pub-92c80eda1059428394970066c8500eda\.r2\.dev\/(renew1028|d2p_v1|wordcraft1014)\//g, '/__assets/$1/');
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === '/__health') {
          res.setHeader('Content-Type', 'application/json'); res.end('{"ok":true}'); return;
        }
        if (!req.url.startsWith('/__assets/')) return next();
        const rel = decodeURIComponent(req.url.split('?')[0].slice('/__assets/'.length));
        const root = rel.startsWith('renew1028/') ? build : prior;
        const file = path.resolve(root, rel);
        if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) {
          res.statusCode = 404; res.end(); return;
        }
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Content-Type', file.endsWith('.webp') ? 'image/webp' : 'application/pdf');
        fs.createReadStream(file).pipe(res);
      });
    }
  }],
  server: { host: '127.0.0.1', port: 8179, strictPort: true, fs: { allow: [home] } }
});
await server.listen();
console.log('Review smoke server: http://127.0.0.1:8179; vite-plugin-console-pipe active');

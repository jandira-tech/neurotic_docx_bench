// Local preview only; saved HTML retains its intended R2 URLs.
import { createServer } from 'vite';
import consolePipe from 'vite-plugin-console-pipe';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const home = path.dirname(fileURLToPath(import.meta.url));
const roots = {
  renew1030: path.join(home, 'build'),
  renew1028: path.resolve(home, '../site_1029/build'),
  d2p_v1: path.resolve(home, '../site_1028/build'),
  wordcraft1014: path.resolve(home, '../site_1028/build'),
};
const site = path.resolve(home, '../..');
const pipe = consolePipe();
const injectPipe = pipe.transformIndexHtml;
pipe.transformIndexHtml = html => {
  const result = injectPipe(html);
  for (const tag of result.tags || []) {
    if (tag.attrs?.src === '@console-pipe/client') tag.attrs.src = '/@console-pipe/client';
  }
  return result;
};
const contentType = file => ({'.webp':'image/webp','.pdf':'application/pdf','.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.woff2':'font/woff2'}[path.extname(file)] || 'application/octet-stream');
function serve(root, relative, res) {
  let file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep) || !fs.existsSync(file)) { res.statusCode=404; res.end(); return; }
  if (fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) { res.statusCode=404; res.end(); return; }
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Content-Type', contentType(file));
  fs.createReadStream(file).pipe(res);
}
const server = await createServer({
  configFile: false, root: path.join(home, 'preview'), publicDir: false,
  cacheDir: path.join(home, '.vite'),
  plugins: [pipe, {
    name: 'local-review-assets',
    transformIndexHtml(html) {
      return html.replace(/https:\/\/pub-92c80eda1059428394970066c8500eda\.r2\.dev\/(renew1030|renew1028|d2p_v1|wordcraft1014)\/[^"'\\\s<>]+/g, (url, prefix) => {
        const parsed=new URL(url);
        const local='/__assets/'+parsed.pathname.slice(1)+parsed.search+parsed.hash;
        // New output must always resolve locally; missing retained bytes stay at their published URL.
        if(prefix==='renew1030')return local;
        let relative;
        try {relative=decodeURIComponent(parsed.pathname.slice(1));} catch {return url;}
        const root=roots[prefix],file=path.resolve(root,relative);
        return file.startsWith(root+path.sep)&&fs.existsSync(file)&&fs.statSync(file).isFile()?local:url;
      });
    },
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        let pathname;
        try { pathname=decodeURIComponent(req.url.split('?')[0]); }
        catch { res.statusCode=400; res.end(); return; }
        if (pathname === '/__health') {
          res.setHeader('Content-Type', 'application/json'); res.end('{"ok":true}'); return;
        }
        if (pathname.startsWith('/__assets/')) {
          const rel=pathname.slice('/__assets/'.length), root=roots[rel.split('/')[0]];
          if (!root) { res.statusCode=404; res.end(); return; }
          return serve(root, rel, res);
        }
        // These existing site resources are read-only fallbacks for the navigation copy.
        const staticPath=pathname.replace(/^\/redlines\/(speed|_static)\//, '/$1/');
        if (/^\/(speed|_static)\//.test(staticPath)) return serve(site, staticPath.slice(1), res);
        return next();
      });
    }
  }],
  server: { host:'127.0.0.1', port:8180, strictPort:true, fs:{allow:[home]} }
});
await server.listen();
console.log('Review smoke server: http://127.0.0.1:8180; vite-plugin-console-pipe active');

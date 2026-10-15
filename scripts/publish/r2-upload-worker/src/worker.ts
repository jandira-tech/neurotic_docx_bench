// R2 upload Worker: a fast, authenticated PUT proxy into the review bucket.
// Deployed from scripts/publish/r2-upload-worker (see docs/PUBLISHING.md):
//   bunx wrangler secret put UPLOAD_SECRET   # a random string, also saved to ~/.ndb/upload-secret
//   bunx wrangler deploy
// Then scripts/publish/upload_r2.py --via-worker <url> sends objects here. Writes are
// non-overwriting (immutable keys) and refuse keys outside the expected prefixes.

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "PUT") {
      return new Response("PUT only", { status: 405 });
    }
    if (request.headers.get("x-secret") !== env.UPLOAD_SECRET) {
      return new Response("bad secret", { status: 401 });
    }
    const key = decodeURIComponent(new URL(request.url).pathname.slice(1));
    if (!key || key.includes("..") || key.length > 1024) {
      return new Response("bad key", { status: 400 });
    }
    const contentType = request.headers.get("content-type") || "application/octet-stream";
    try {
      const existing = await env.MEDIA.head(key);
      if (existing) {
        return new Response("exists", { status: 412 }); // keys are immutable: never overwrite
      }
      await env.MEDIA.put(key, request.body, {
        httpMetadata: { contentType, cacheControl: "public, max-age=31536000, immutable" },
      });
      return new Response(null, { status: 200 });
    } catch (error) {
      return new Response(`put failed: ${error}`, { status: 500 });
    }
  },
};

interface Env {
  MEDIA: R2Bucket;
  UPLOAD_SECRET: string;
}

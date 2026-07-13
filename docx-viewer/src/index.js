export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Serve the manifest with a JSON content type.
    if (url.pathname === "/manifest.json") {
      const res = await env.ASSETS.fetch(new Request("https://dummy/manifest.json", request));
      return new Response(res.body, {
        headers: { "content-type": "application/json; charset=utf-8" },
      });
    }

    // Everything else (HTML page, .docx assets) is served by the static
    // assets binding. Cloudflare serves .docx with the right content-type
    // automatically.
    return env.ASSETS.fetch(request);
  },
};

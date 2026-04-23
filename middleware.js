// Basic-auth gate for the whole site. Runs on Vercel's Edge before any
// static asset is served. To enable, set SITE_USER and SITE_PASS in
// Vercel project environment variables. If either is unset, the site is
// open (useful for local preview / a temporarily public deploy).
//
// For a real "password protection" experience rather than the browser's
// basic-auth dialog, upgrade to Vercel Pro's built-in Password Protection.
// This middleware is the free alternative.

export const config = {
  // Exclude Vercel's internal endpoints; everything else is protected.
  matcher: "/((?!_vercel).*)",
};

export default function middleware(request) {
  const expectedUser = process.env.SITE_USER;
  const expectedPass = process.env.SITE_PASS;

  // If no credentials configured, pass through (open site).
  if (!expectedUser || !expectedPass) return undefined;

  const auth = request.headers.get("authorization");
  if (auth && auth.startsWith("Basic ")) {
    const encoded = auth.slice(6);
    try {
      const [user, pass] = atob(encoded).split(":");
      if (user === expectedUser && pass === expectedPass) {
        return undefined; // authorized; serve the requested asset
      }
    } catch (_) {
      // fall through to 401
    }
  }

  return new Response("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Regulatory Settlement Replication"',
    },
  });
}

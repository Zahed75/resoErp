# Cloudflare Origin CA for Resort Cloud tenants

Origin CA certificates only work for traffic proxied through Cloudflare,
which is exactly the setup we want: TLS terminates at Cloudflare's edge
for guests and between Cloudflare and nginx with a 15-year origin cert.

## Steps

1. In the Cloudflare dashboard pick the `resocloud.example.com` zone ->
   **SSL/TLS -> Origin Server -> Create Certificate**.
2. Choose **Wildcard** `*.resocloud.example.com` (optionally also the apex
   in a second cert). Leave ECC default, validity 15 years.
3. Copy the **Origin Certificate** to `/etc/nginx/certs/resocloud-origin.pem`
   and the **Private Key** to `/etc/nginx/certs/resocloud-origin.key`
   (chmod 600 the key). Store a backup of both in the team vault.
4. SSL/TLS mode: **Full (strict)** — required, otherwise the origin cert
   is not validated and loops can occur.
5. Create the wildcard DNS record: `*.resocloud.example.com` as a
   **Proxied (orange cloud)** CNAME/A record pointing to the origin IP,
   plus the apex record.
6. `nginx -t && systemctl reload nginx`.
7. Verify: `curl -I https://demo.resocloud.example.com` should hit the
   tenant vhost and return an Odoo response.

Renewal: Origin CA certs can be re-issued from the same dashboard page at
any time; schedule a calendar reminder even at 15-year validity.

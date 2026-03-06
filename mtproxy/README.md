# MTProto Proxy Deployment

This folder contains Docker Compose config for running your own Telegram MTProto proxy.

## 1. Prepare VPS

- Rent a VPS outside Russia (Ubuntu 22.04+ is fine).
- Open `443/tcp` in cloud firewall and on server firewall.
- Install Docker and Docker Compose plugin.

## 2. Run proxy

```bash
cd mtproxy
docker compose up -d
```

## 3. Get connection links

```bash
docker logs mtproto-proxy
```

In logs you will see links like:

- `tg://proxy?...`
- `https://t.me/proxy?...`

Copy the `https://t.me/proxy?...` link and set it in your bot with:

```text
/setproxy https://t.me/proxy?server=...&port=...&secret=...
```

## 4. Security hardening

- Keep VPS updated (`apt update && apt upgrade`).
- Allow SSH only with keys, disable password auth.
- Use fail2ban/ufw.
- Keep backup access to server credentials.

## 5. Optional monetization tag

If you want Telegram ad revenue from proxy traffic, connect your proxy to `@MTProxybot` as described in Telegram docs.

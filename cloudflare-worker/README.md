# TimeSliceIQ - Cloudflare Worker YouTube Proxy

This Cloudflare Worker routes YouTube transcript requests from Cloudflare's global edge network to bypass AWS / Vercel datacenter IP blocks.

---

## 3-Step Setup Guide (Free & Takes 2 Minutes)

### Step 1: Create a Free Cloudflare Worker
1. Go to [dash.cloudflare.com](https://dash.cloudflare.com/) (create a free account if you don't have one).
2. In the left navigation, click **Workers & Pages** (or **Compute (Workers)**).
3. Click **Create Application** $\rightarrow$ **Create Worker**.
4. Name your worker (e.g. `timeslice-proxy`), then click **Deploy**.

---

### Step 2: Paste the Worker Code
1. On the worker overview page, click **Edit code** (in the top right corner).
2. Replace all the default code in `worker.js` with the contents of [`worker.js`](./worker.js).
3. Click **Deploy** in the top right corner.
4. Copy your Worker URL from the top bar. It will look like:
   ```text
   https://timeslice-proxy.<your-subdomain>.workers.dev
   ```

---

### Step 3: Configure TimeSliceIQ on Vercel
1. Open your [Vercel Dashboard](https://vercel.com/dashboard) $\rightarrow$ Project **timesliceiq**.
2. Go to **Settings** $\rightarrow$ **Environment Variables**.
3. Edit (or add) `YT_PROXY_URL`:
   * **Key**: `YT_PROXY_URL`
   * **Value**: `https://timeslice-proxy.<your-subdomain>.workers.dev`
4. Click **Save**.
5. Trigger a redeploy:
   ```powershell
   vercel --prod
   ```

---

### Verification
You can verify your worker is active by opening its URL in your browser:
```text
https://timeslice-proxy.<your-subdomain>.workers.dev
```
It should return:
```json
{
  "status": "ok",
  "service": "TimeSliceIQ YouTube Proxy Worker",
  "usage": "/?url=https://www.youtube.com/watch?v=VIDEO_ID"
}
```

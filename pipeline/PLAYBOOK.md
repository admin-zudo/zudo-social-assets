# Zudo Works – Article Social Pack: daily playbook

Agreed with Arun (Arunkumar V, CTO) on 12 November 2026. Every run follows this file from top to bottom, on its own, without asking anything.

## 0. What one run does
1. Pick the newest zudoworks.com Insights article that has not had a social pack yet.
2. Make the assets: a 4-slide carousel in 4 colour themes, and one 40–50 s animated explainer video in three shapes (9:16, 16:9, 1:1), plus a 9:16 version without people.
3. Upload the video to YouTube first: a Short (9:16) and a normal video (16:9), both public, with full video SEO.
4. Only after YouTube succeeds: update the article page with the video and video schema, post Reels and LinkedIn videos, and schedule the carousels on every Zoho Social channel.
5. Add the links to the article page ("Watch and share"), back-fill yesterday's post links, and send Arun a Telegram report.

One wave per day only. If there is no new article, do only step 5 (back-fill) and report "no new article".
No posting on Sundays (Arun's standing rule; use India time): on Sunday build nothing and post nothing.

## 1. Fixed rules (never break)
- **Audience:** United States, United Kingdom, Australia and New Zealand. Nothing that reads as Indian; never write "Chennai". British spelling by default; US spelling only in a caption written specifically for US readers.
- **Truth:** every number, step and claim comes from the article itself. No invented numbers, customers, quotes or reviews; example figures are labelled "Example" on screen. Never call Zudo Works a "Zoho Partner". Never name clients of Arun's previous employer. No other vendors' prices.
- **AI wording:** never mention AI-generated images or voice in any caption, description, image or page. The only disclosure is YouTube's own "altered or synthetic content" setting (Make input `synthetic: "yes"`). Instagram and Facebook **Reels use the version without people** (`?nopeople=1`), because Meta requires a label for photorealistic video. Still-image carousels with people are fine on every platform.
- **Quality bar (Arun's words: "advanced", "very attractive", "not AI slop"):** style A look, bold type, clean motion, no glows, sparkles, gradients or stock-looking clip art. Text must never overlap a person (run `check_overlap.py`; it must print NO OVERLAP). Look at every image and a contact sheet of the video before anything is published.
- **No X (Twitter)** posting from this pipeline (bot-flag risk). Never create, change, fire or delete any scheduled task.
- **Make.com is on the free plan:** before any Make run, call `organizations_get` (organisation 9384903). If `unusedTransfer` is under 40,000,000 bytes or `unusedOperations` under 40, skip the Make steps for today (YouTube and Reels), skip the social wave, and report it.

## 2. Setup (every run, fresh sandbox)
```
pip install -q --break-system-packages kokoro-onnx faster-whisper "rembg[cpu]" playwright soundfile
mkdir -p /home/claude/kokoro && cd /home/claude/kokoro
for f in kokoro-v1.0.onnx voices-v1.0.bin; do [ -f $f ] || curl -sSL -o $f https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f; done
```
Repos (load `mcp__claude-code-remote__add_repo` via ToolSearch):
- `admin-zudo/zudo-social-assets` with access "push", cloned to /home/claude/zudo-social-assets. The kit lives in `pipeline/` (this file, scripts, templates); state in `pipeline/state.json`; assets in `social/<YYYY-MM-DD>-<slug>/`.
- `admin-zudo/officemaintenance` with access "push", cloned to /home/claude/officemaintenance (website). Read `tools/seo/DAILY-ARTICLE-RUN.md` for its build chain and checks before editing any page. Always `git pull --rebase` before pushing (the daily article run also pushes to main). Never force-push.
Copy the kit into a work folder: `cp -r /home/claude/zudo-social-assets/pipeline /home/claude/work && cd /home/claude/work`, and download the logo: `curl -sSL -o logo.svg https://zudoworks.com/Asset/brand/zudo-works-logo.svg` (copy it next to every HTML file).

## 3. Choose the article
- **Primary source:** `blog/.article-releases.json` in officemaintenance (written by the daily article run). Its `releases` list has one entry per published article: `released_at` (India time, ISO with +05:30), `slot` ("night" or "evening") and `url`. Newest is last.
- Take the newest entry (by `released_at`) whose URL is not in `state.json` → `processed`. Only consider articles released in the last 48 hours; older unprocessed ones are skipped (record them as skipped in state.json).
- Fallback only if that file is missing or unreadable: use https://zudoworks.com/sitemap.xml and the order on https://zudoworks.com/insights/, and say so in the Telegram report.
- Read the live page (WebFetch) and its source in the repo (`tools/insights/articles_r<YYYYMM>.py`). Record the slug, URL and `released_at` in state.json when done.
- Write `plan.json`: hook (max 8 words), the 3 most useful facts or mistakes, 7–9 voice lines (one per scene), carousel text for 4 slides, platform captions (section 7), YouTube metadata (section 6).

## 4. People images (fresh for every article)
- Use `mcp__Hugging_Face_Spaces__gr1_z_image_turbo_generate`, resolution "896x1152 ( 7:9 )". 4 people, each in a pose that matches one slide or scene (thinking, ticking a checklist, shrugging, pointing at the viewer, arms crossed confident, looking at a laptop, etc.).
- Prompt pattern: "Professional studio photograph, black and white, of a <person> <pose>, <expression>. Waist-up, <view>, soft studio lighting, plain pure white background, sharp focus, realistic, editorial portrait. Plain clothing with no text, no print and no logo."
- Mix ages, genders and ethnicities that reflect US, UK, Australian and New Zealand workplaces. Never a real or famous person. Look at each result: reject any with text, logos, extra fingers or odd hands, and regenerate.
- The tool result gives a local .webp path; copy it, then `python3 cutout.py in.webp out.png ...`.

## 5. Carousel (4 slides × 4 themes)
- Start from `carousel_example/` (slide1–4.html + base.css): slide 1 hook cover, slide 2 the steps or list, slide 3 the key insight or comparison, slide 4 numbers plus "Comment ↓" and "Save this". Keep style A: yellow side bar, huge headline with highlight, red numbers, page dots and "Swipe →".
- Each slide gets one person (white outline, in open space). Rewrite all text for this article; keep facts exact.
- Themes by platform (add the class to `<body>`): Instagram `theme-white` (default, no class), LinkedIn page and profile `theme-navy`, Facebook `theme-blue`, Threads, Mastodon and Google Business `theme-amber`.
- Render 1080×1350 with Playwright to PNG, then JPEG quality 90 for Instagram (max 8 MB). Run `check_overlap.py` on the slide files. Open and look at every slide in every theme; fix contrast or crowding before continuing.

## 6. Video (bold voice, fast beat, advanced animation)
1. `script.json` → `{"lines":[{"say":..., "show":...}]}`. `say` may respell for pronunciation (e.g. "Air table", "zudo works dot com"); `show` is the caption text exactly as it should read. No "I'm Arunkumar", no presenter. Last line: a call to read the full guide at zudoworks.com.
2. `python3 voice.py script.json`, then read `qc.txt`: every line must score 0.85 or more. Otherwise respell that sentence and run again.
3. `T = VOICE_END + 4.5` seconds.
4. Write `video.html` from `video_example.html`: keep its CSS and the animation engine (masked word reveals, highlight draw-on, yellow and black wipes, camera push, pop and spring motion, people sliding in, active-word caption chip, moving grid, `?nopeople` switch). Replace the scenes with one scene per voice line (`s0`..`sN`), each with a fresh visual that explains that line (checklists, counters, timers, flows, before/after, cards, crossed-out items). Put people in 3–4 scenes, beside content and never over it.
5. `events.json`: pops when cards appear, ticks for timers, a ding for a success moment, a riser into the final scene (scene changes and the opening impact are added automatically).
6. `python3 audio.py T events.json`, then `python3 check_overlap.py --video video.html T` (must print NO OVERLAP).
7. Render: `python3 render.py video.html v916.mp4 T` (with people) and `python3 render.py video.html v916_np.mp4 T 1080 1920 nopeople=1`.
8. Fill `panel_169.html` and `panel_11.html` (`{{TAG}}`, `{{TITLE_HTML}}`, `{{POINTS_LI}}`, `{{QUESTION}}`), screenshot at 1920×1080 and 1080×1080, then `python3 compose.py v916.mp4 p169.png p11.png v169.mp4 v11.mp4`.
9. Extract 8 frames from v916.mp4 into a contact sheet and look at it. Transcribe the final audio with faster-whisper as a last check. Fix anything wrong before uploading.

## 7. Captions (same facts, different style per platform)
- **YouTube Short:** title under 70 characters with the main keyword plus "#Shorts"; description of 2–3 lines with the article link first.
- **YouTube normal video:** keyword-first title (under 70 characters, may name the region, e.g. "for UK manufacturers"); description of 1,500–2,500 characters: article link first, summary, chapters with timestamps from `tl.json` (first one 00:00), key facts, the call to action, then 3 hashtags; 10–15 tags. Category 28.
- **LinkedIn profile (Arun's own voice, first person):** 1,300–2,000 characters, personal hook in the first two lines, short paragraphs, practical points, a question at the end, 3–5 hashtags. Article link only in the first comment.
- **LinkedIn page (company voice):** 900–1,500 characters, different opening and structure, link in the first comment, 3–5 hashtags.
- **Instagram:** a punchy hook, value in short lines, "Full guide: link in bio", a question, 5 hashtags at most. Location tag: rotate London, Manchester, Birmingham, Sydney, Melbourne, Auckland, Chicago, Houston (`getSocialGeolocations`).
- **Facebook:** conversational, 400–900 characters, article link in the text, question at the end, 3 hashtags, location tag as on Instagram.
- **Threads:** under 480 characters, with the link. **Mastodon:** under the channel's `max_characters`, with the link. **Google Business:** under 1,400 characters, call-to-action LEARN_MORE pointing to the article.
- **Hashtags:** mix topic tags (e.g. #ZohoCreator, #Manufacturing, #NoCode, #ERP) with region tags (#UKManufacturing, #MadeInBritain, #AussieManufacturing, #NZManufacturing, #USManufacturing), rotating so no two days repeat the same set.
- Every caption is written fresh. No sentence is reused between platforms, no hype, no invented numbers.

## 8. Publish order (stop at the first failure and report it)
1. **Assets:** commit `social/<date>-<slug>/` (all JPGs and MP4s) to zudo-social-assets and push. Raw URL: `https://raw.githubusercontent.com/admin-zudo/zudo-social-assets/main/<path>`; LinkedIn needs the jsDelivr URL `https://cdn.jsdelivr.net/gh/admin-zudo/zudo-social-assets@main/<path>`.
2. **YouTube:** run Make scenario 8126018 (`scenarios_run`, responsive true): first the Short (v916.mp4), then the normal video (v169.mp4), both with `privacy: "public"`, `publish_at: ""` and `synthetic: "yes"`. Keep both video IDs. If an upload fails, retry once; if it fails again, post nothing else today, send "Article Social Pack: PROBLEM" on Telegram, and leave the article unprocessed so tomorrow's run retries it.
3. **Page update (officemaintenance):** in the article's source, add a "Watch" block just after the quick answer: a click-to-load YouTube embed (thumbnail `https://i.ytimg.com/vi/<ID>/hqdefault.jpg`, iframe from youtube-nocookie.com loaded on click, title text, accessible button). Add `VideoObject` JSON-LD with name, description, thumbnailUrl, uploadDate (ISO with offset), duration (ISO 8601), embedUrl, contentUrl and transcript (the `show` lines). Add a "Watch and share" section at the bottom with the YouTube video and Short links (social links are added the next day). Use the site's existing template and generators, run the full build chain and checks from DAILY-ARTICLE-RUN.md, check desktop and phone widths, `git pull --rebase`, commit, `git push origin HEAD:main`. Confirm the live page with WebFetch and Lighthouse SEO 100; if it's broken and can't be fixed, revert and push.
4. **Reels and LinkedIn video** (Make scenario 8132416): `instagram` and `facebook` with **v916_np.mp4** (raw URL, `cover_ms` 1200); `linkedin_page` and `linkedin_profile` with **v11.mp4** (jsDelivr URL). Each with its own caption from section 7. Record the returned post IDs.
5. **Carousels (Zoho Social):** portal 60084987736, brand 426275000000012009 (check with getSocialPortals and getSocialBrands; get channels with getSocialChannels). Upload each slide with `uploadSocialMediaFromUrl` (raw URLs) and compare width, height and size. For each channel: `validateSocialPost`, then `createSocialSchedule` type 1, 4 images in the platform's theme, its caption, `first_comment` with the link on LinkedIn, and a geo tag on Instagram and Facebook. Schedule times (India time, today): Instagram 7:05 PM, LinkedIn page 7:35 PM, LinkedIn profile 8:05 PM, Facebook 8:35 PM, Threads 9:05 PM, Mastodon 9:35 PM, Google Business 10:05 PM (cover slide only, call to action). These hit the US morning and the UK afternoon; keep at least 30 minutes between posts.
6. **State:** add the slug, date, YouTube IDs, Make post IDs and Zoho schedule IDs to `pipeline/state.json`; commit and push.

## 9. Back-fill (start of every run)
For the previous processed article: use `getSocialPublishedPosts` and `getSocialPublishedPostDetail` to get the live permalinks of yesterday's Zoho posts, plus the Reels and LinkedIn videos where their IDs give a link. Add them to that article's "Watch and share" section (one line per platform, opening in a new tab, `rel="noopener"`), rebuild, check, and push in one commit. Mark it done in state.json.

## 10. Telegram report (`telegram_send`, html true)
```
<b>Article Social Pack</b>
<b>Article:</b> <a href="...">title</a>
<b>YouTube:</b> <a href="...">video</a> · <a href="...">Short</a>
<b>Posted now:</b> Instagram Reel, Facebook Reel, LinkedIn page video, LinkedIn profile video
<b>Scheduled:</b> carousels with times (India time)
<b>Page:</b> video added (yes or no), back-filled links (n)
<b>Assets:</b> link to the social/<date>-<slug>/ folder on GitHub
Problems or anything Arun must do (or "nothing needed").
```
If something failed, send a separate bold "Article Social Pack: PROBLEM" message straight away.

## 11. Finish
End with at most three plain sentences: what was published, what's scheduled, and anything Arun must do.

## One-time manual steps for Arun (already told to him)
- Instagram bio link: set it once to https://zudoworks.com/insights/ (newest article first), since captions say "link in bio".
- YouTube "altered or synthetic content" is ticked automatically through the Make scenario.

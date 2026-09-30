---
name: xiaohongshu-chrome-devtools
description: Use when extracting visible Xiaohongshu note text, comments, metadata, or search results through Chrome DevTools MCP.
argument-hint: [note-url-or-keyword]
allowed-tools: chrome-devtools_navigate_page, chrome-devtools_new_page, chrome-devtools_take_snapshot, chrome-devtools_evaluate_script, chrome-devtools_click, chrome-devtools_fill, chrome-devtools_type_text, chrome-devtools_press_key, chrome-devtools_wait_for, chrome-devtools_hover, chrome-devtools_take_screenshot, chrome-devtools_list_pages, chrome-devtools_select_page, Read
---

# Xiaohongshu Note Search & Extract via Chrome DevTools

Extract note URL or search keyword: $ARGUMENTS

## Safety Rules

- Use only Chrome DevTools MCP browser tools and the local scripts in `scripts/`.
- Extract only visible note/search/comment content and whitelisted structured content fields.
- Never inspect credentials, cookies, browser storage, auth/session state, request signatures, or hidden internal APIs.
- Never automate login, SMS, QR code, CAPTCHA, liking, following, commenting, collecting, publishing, messaging, or notifications.
- Never bypass access controls or login walls. If a login wall appears, stop and ask the user to log in manually in the browser.
- Never download or save images. You may count visible images as metadata only.
- Validate Xiaohongshu URLs before navigation; reject non-Xiaohongshu domains and unsafe protocols.
- Do not spoof browser fingerprint values. Local context checks are read-only diagnostics.

## Constants

- **MAX_RESULTS = 10** - Default number of search results for keyword mode.
- **INCLUDE_COMMENTS = false** - Top-level comments are disabled unless explicitly requested.
- **DEFAULT_COMMENT_COUNT = 10** - Default number of top-level comments to extract when comments are enabled.
- **DEFAULT_INDEX = 1** - Default 1-based index for selecting a search result.
- **READ_DELAY_MS = 700-1800** - Default reading pause range.
- **JITTER_RATIO = 0.25** - Randomize pacing by about +/-25%.
- **SCROLL_STEP_PX = 220-480** - Default progressive scroll distance.
- **MAX_SCROLL_STEPS = 6** - Default progressive scroll attempts per pacing pass.
- **STABLE_ROUNDS = 2** - Stop loading loops when page height or visible count remains stable.

> Overrides (append to arguments):
> - `/xiaohongshu-chrome-devtools "https://www.xiaohongshu.com/explore/NOTE_ID"` - extract one note with defaults
> - `/xiaohongshu-chrome-devtools "https://www.xiaohongshu.com/explore/NOTE_ID" - comments` - include top-level comments
> - `/xiaohongshu-chrome-devtools "https://www.xiaohongshu.com/explore/NOTE_ID" - comments: 20` - include 20 top-level comments
> - `/xiaohongshu-chrome-devtools "keyword: LLM reasoning"` - search notes by keyword
> - `/xiaohongshu-chrome-devtools "keyword: AI tutorial" - max: 20` - search with custom result limit
> - `/xiaohongshu-chrome-devtools "keyword: tutorial" - index: 3` - select 3rd search result for extraction
> - `/xiaohongshu-chrome-devtools "https://..." - no-comments` - explicitly disable comments

## Reusable Scripts

The repeatable DevTools JavaScript lives outside this document so the workflow stays short.

- `scripts/context-preflight.js` - read-only locale, timezone, viewport, and URL diagnostics. Use before extraction after the first Xiaohongshu page is loaded.
- `scripts/human-pacing.js` - parameterized reading pause, jitter, progressive scroll, and stabilization helper. Use before snapshots, before extraction, and while loading comments.

When a script is needed, read it with `Read`, then pass its function expression to `chrome-devtools_evaluate_script`. You may adjust only the options object passed to the function; do not edit the script during normal extraction.

## Workflow

### Step 1: Parse Arguments

Parse `$ARGUMENTS` for directives:

- **Note URL**: main argument matching `xiaohongshu.com/explore/...`, `xiaohongshu.com/discovery/item/...`, or `xhslink.com/...`
- **Keyword query**: `keyword: QUERY`, `search: QUERY`, or plain text without a Xiaohongshu URL
- **`- max: N`** or **`- limit: N`**: override MAX_RESULTS for search
- **`- index: N`**: select Nth search result (1-based, default 1)
- **`- comments`**: enable top-level comments with DEFAULT_COMMENT_COUNT
- **`- comments: N`**: enable comments with explicit count N
- **`- no-comments`**: explicitly disable comments

If the argument is a Xiaohongshu URL, continue to Step 4. If it is a keyword query, continue to Step 3.

### Step 2: Preflight, Pacing, and Login Wall Detection

Run this step after every navigation and before any extraction.

1. Use `chrome-devtools_wait_for` for a visible page marker such as result tabs, a note title, author text, or body content.
2. Read `scripts/context-preflight.js` and run it with `chrome-devtools_evaluate_script`.
3. If warnings mention a non-Chinese locale, non-China timezone, very small viewport, or non-Xiaohongshu URL, report the warning briefly. Continue only when content is visible and no login wall is present.
4. Read `scripts/human-pacing.js` and run it once with default options to simulate reading and progressive scrolling.
5. Use `chrome-devtools_take_snapshot` to inspect the page state.
6. Check login wall phrases and stop immediately if any appear without note/search content:
   - `登录后查看搜索结果`
   - `登录后查看`
   - `手机号登录`
   - `获取验证码`
   - `扫码`
   - `登录探索更多内容`
   - `请先登录`

When a login wall is detected, tell the user: `小红书需要登录才能查看该内容。请在浏览器中手动登录后告诉我继续。` After user confirmation, retry once. If it persists, report failure and stop.

### Step 3: Search Notes by Keyword

**Primary method - direct URL navigation:**

1. Construct `https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_explore_feed`.
2. Use `chrome-devtools_navigate_page` with `type="url"` to navigate.
3. Run Step 2 before extracting results.
4. Treat tabs such as `全部`, `图文`, `视频`, `用户` as loading/context indicators only.

**Fallback method - search box input:**

If direct navigation fails, redirects, or shows unexpected content:

1. Navigate to `https://www.xiaohongshu.com/explore`.
2. Run Step 2.
3. Use `chrome-devtools_take_snapshot` to locate the search textbox.
4. Click the search textbox, type the keyword, and press Enter.
5. Run Step 2 again after search results load.

**Result extraction:**

1. Use `chrome-devtools_take_snapshot` after pacing.
2. Find link elements containing note URLs.
3. Extract up to MAX_RESULTS:
   - **Title**
   - **Author**
   - **Date** if visible
   - **Likes** if visible
   - **Note URL**
4. Present results as `# | Title | Author | Date | Likes | URL`.

**Result selection:**

- If `- index: N` is specified, select that 1-based result.
- Otherwise select the first result by default.
- Click the corresponding link uid, then continue to Step 4.

### Step 4: Open and Extract Note Content

**Opening the note:**

- From search results: click the selected note link, wait for title/author/body markers, then run Step 2.
- From direct URL: navigate to the note URL, wait for title/author/body markers, then run Step 2.

**Primary extraction - accessibility snapshot:**

1. Use `chrome-devtools_take_snapshot` with `verbose=false`.
2. Extract:
   - **Title** from main title text
   - **Author** from author link/avatar text
   - **Body text** from visible body paragraphs
   - **Tags/Hashtags** from visible `#` links/text
   - **Interaction counts** near like/collect/comment icons
   - **Date/Location** from visible publish/edit metadata
   - **Image count** from visible image elements if easy to identify
   - **URL** from current page

**Fallback extraction - page evaluation:**

If snapshot extraction is incomplete, use `chrome-devtools_evaluate_script` only for visible-content fields or whitelisted structured note fields. Return only JSON-serializable strings, numbers, arrays, and plain objects. Never return raw page state.

Allowed fields:

| Field | Source |
|-------|--------|
| title | Snapshot or whitelisted page data |
| author | Snapshot or whitelisted page data |
| body | Snapshot or whitelisted page data |
| tags | Visible tags or whitelisted page data |
| likes | Visible interaction count |
| collects | Visible interaction count |
| comments_count | Visible interaction count |
| date | Visible publish/edit metadata |
| location | Visible location metadata |
| images_visible | Visible image count only |
| url | Current page URL |

### Step 5: Extract Comments (Optional)

Only run this step if the user passed `- comments` or `- comments: N`.

1. Use `chrome-devtools_take_snapshot` to verify comment availability (`说点什么...`, comment count, or comment section).
2. If comments are unavailable, report `Comments not available for this note` and continue to Step 6.
3. Run `scripts/human-pacing.js` with a slightly larger `maxSteps` to progressively approach the comment section. Do not jump directly to the document bottom.
4. Wait briefly, take a snapshot, and count visible top-level comments.
5. Repeat pacing/snapshot until target count is reached, no more comment elements appear, or page height/comment count is stable for STABLE_ROUNDS.
6. If a `查看更多评论` or similar control is visible and target count is not reached, click it, wait, run pacing, and snapshot again. Stop after 5 load-more attempts or stabilization.

Extract top-level comments only:

| Field | Source |
|-------|--------|
| # | 1-based index |
| Commenter | Visible commenter name |
| Date | Visible date/relative time |
| Text | Visible comment body |
| Likes | Visible like count |

If fewer comments load than requested, include all visible comments and mention the actual count.

### Step 6: Final Output

#### Search Results

```text
| # | Title | Author | Date | Likes | URL |
|---|-------|--------|------|-------|-----|
| 1 | [title] | [author] | [date] | [likes] | [url] |
```

#### Note Extraction

```text
| Field    | Value                  |
|----------|------------------------|
| Title    | [note title]           |
| Author   | [author name]          |
| Date     | [edit/publish date]    |
| Location | [location if present]  |
| Likes    | [like count]           |
| Collects | [collect count]        |
| Comments | [comment count]        |
| Images   | [visible image count]  |
| Tags     | [comma-separated tags] |
| URL      | [note URL]             |
```

Follow with the full extracted body text.

#### Comments

```text
| # | Commenter | Date | Text | Likes |
|---|-----------|------|------|-------|
| 1 | [name] | [date] | [text] | [likes] |
```

Always end with:

- `Extracted note: [title]` or `Found N notes for "[keyword]"`
- `Comments: included (N)` or `Comments: excluded by default`
- Any warnings: login wall, local context mismatch, partial comment extraction, or unstable loading

## Examples

```text
/xiaohongshu-chrome-devtools "https://www.xiaohongshu.com/explore/NOTE_ID"
/xiaohongshu-chrome-devtools "https://www.xiaohongshu.com/explore/NOTE_ID" - comments
/xiaohongshu-chrome-devtools "https://www.xiaohongshu.com/explore/NOTE_ID" - comments: 20
/xiaohongshu-chrome-devtools "keyword: LLM reasoning"
/xiaohongshu-chrome-devtools "keyword: AI tutorial" - index: 3
/xiaohongshu-chrome-devtools "keyword: tutorial" - comments
```

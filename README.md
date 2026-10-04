# Bookmark

Bookmark lets you maintain all your frequently used links as code and host
them on the web (for example, GitHub Pages). Set the published page as the
home page in every browser on every device for personal use. The result is
cross-browser and stays in sync across your devices.

## How it works

You keep your bookmarks in an HTML file, track changes with Git, and host the
result as a site on GitHub Pages. The conversion script turns the exported
HTML into Markdown, and MkDocs builds both into a browsable site.

- You maintain your most-used links as code in an HTML file.
- Git tracks every change, so your history is versioned.
- GitHub Pages hosts the built site as your personal home page.
- You set this page as the home page across your iPhone, iPad, Windows PC, and
  Ubuntu machines.
- When you find a new link, you commit it, and the update takes effect
  everywhere after the site redeploys.

## Bookmark sync solutions

Several tools can keep bookmarks in sync between browsers and devices. This
project uses the last approach: an HTML bookmark file hosted on GitHub.

- Xmarks syncs bookmarks between browsers.
- [Raindrop.io](https://app.raindrop.io/my/0/) is a browser extension that
  syncs bookmarks between browsers.
- The "Bookmarks Anywhere" Chrome extension lets you access bookmarks as HTML.
- An HTML bookmark file set as the home page syncs across devices and browsers.
  Store it in OneDrive or GitHub to sync across devices and networks.

## 跨设备跨浏览器 + 书签即代码

用 HTML 代码的形式维护管理常用网址，用 Git 跟踪，并托管在 GitHub Pages 作为单页面网页。

在我的 iPhone、iPad、Windows PC、Ubuntu 机器上，各种浏览器都把这个页面设为主页。

这样可以随时随地访问我的常用网址，并保持同步。

遇到新的有趣网址时，可以随时以代码的形式提交到 GitHub，更新会在任何地方生效。

## Project layout

The repository separates the bookmark sources, the conversion script, and the
site configuration.

- `docs/bookmark.html` and `docs/bookmark-edge.html` are the exported browser
  bookmark files.
- `docs/bookmark.md` and `docs/bookmark-edge.md` are the Markdown versions that
  MkDocs renders.
- `src/btm.py` converts an exported HTML bookmark file to Markdown.
- `mkdocs.yml` configures the MkDocs Material site.
- `.github/workflows/deploy.yml` builds and deploys the site to GitHub Pages on
  every push to `master`.

## Run locally

You need Python 3.12 or later. These steps create a virtual environment,
install the dependencies, and start a local preview server with live reload.

1. Create and activate a virtual environment:

   ```sh
   python -m venv .venv
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   # macOS or Linux
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Start the preview server:

   ```sh
   mkdocs serve
   ```

The site is served at <http://127.0.0.1:8000/>.

## Deploy to GitHub Pages

The project deploys to the `gh-pages` branch, which GitHub Pages serves. You
can deploy automatically or manually.

### Automatic deployment

The `.github/workflows/deploy.yml` workflow builds and deploys the site on
every push to `master`. For the workflow to push to `gh-pages`, confirm these
repository settings on GitHub once:

- **Settings** > **Actions** > **General** > **Workflow permissions**: select
  **Read and write permissions**.
- **Settings** > **Pages** > **Build and deployment**: set the source to
  **Deploy from a branch** and the branch to **gh-pages** / **/ (root)**.

### Manual deployment

To build and publish directly from your machine, run:

```sh
mkdocs gh-deploy --force --clean
```

This command builds the site and force-pushes it to the `gh-pages` branch.

## Convert HTML bookmarks to Markdown

After you export bookmarks from your browser as HTML, convert them to the
Markdown files that MkDocs renders:

```sh
python ./src/btm.py ./docs/bookmark.html > ./docs/bookmark.md
python ./src/btm.py ./docs/bookmark-edge.html > ./docs/bookmark-edge.md
```

## Comments

The site template includes an optional comment widget powered by
[giscus](https://giscus.app). It's turned off by default through the
`extra.disqus` key in `mkdocs.yml`. To enable comments, set up giscus against
your own repository and provide the generated values in
`overrides/partials/content.html`.

## Reference

- [bookmarkdown](https://pypi.org/project/bookmarkdown): a package that parses
  a browser's exported HTML bookmark file to Markdown.
- [convert-bookmarks.js](https://github.com/gullwing-io/bookworms/blob/main/src/convert-bookmarks.js):
  a JavaScript bookmark converter.
- [Datawrapper](https://www.datawrapper.de/charts): a tool to generate charts
  from data.
- [WiKi for Sufe Courses](https://shenhao-stu.github.io/WiKi-for-Sufe-Courses):
  a MkDocs site this project references.

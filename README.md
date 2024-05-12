# Bookmark

Maintains all frequently used bookmarks in code and host on the web(ex.github page), set the web page as home page on every browsers on every devices for personal use. it is cross browsers and keep in sync with devices.

## Bookmark Sync Solution

- Xmarks Bookmarks sync between browsers
- ChromeExtension "Bookmarks Anywhere" and access using html.
- An html format bookmark file be set as home page across devices and sync between browsers.
  - When saved in OneDrive or GitHub, can sync the bookmarks across devices and network.

## 跨设备跨浏览器+ 书签即代码

用HTML代码的形式维护管理常用网址，用Git跟踪，并托管在GitHub Page作为单页面网页。

在我的iPhone, iPad, Windows PC, Ubuntu 机器上面各种浏览器设置这个页面为主页。

这样可以随时随地访问到我的常用网址，并保持同步。

如果遇到新的有趣的网址，可以随时以代码的形式提交到GitHub上，更新会在任何地方产生作用。

### bookmark html to markdown

[bookmarkdown](https://pypi.org/project/bookmarkdown "Parse browser exported HTML bookmark file to Markdown.")


https://github.com/gullwing-io/bookworms/blob/main/src/convert-bookmarks.js

## Tools

- 数据生成图表 - <https://www.datawrapper.de/charts>


# Run Locally

```sh

conda create -n bookmark python=3.12.2

conda activate bookmark

pip3 install -r requirements.txt

mkdocs serve

```


## GitHub Page

```sh
mkdocs gh-deploy

```

## Convert "bookmarks.html" to markdown and write to "bookmark.md"

```sh
btm bookmarks.html > bookmark.md
```


## Reference

1. <https://shenhao-stu.github.io/WiKi-for-Sufe-Courses>
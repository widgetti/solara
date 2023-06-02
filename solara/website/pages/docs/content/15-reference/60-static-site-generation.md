## Static Site Generation
## Introduction
Solara's static site generation (SSG) feature allows you to pre-render HTML for your website, improving the user experience by providing quick page loads. When a user requests a page, the pre-rendered HTML is served directly to the user. After the page is displayed, the Solara server will connect and take over rendering to make the page interactive.

Using SSG is mostly useful when the content of your website is the same for all users. This is the case for this page (the Solara page itself).

## Benefits of SSG
Another benefit of using SSG is improved search engine optimization (SEO). By allowing web crawlers to index your pages, you can improve the visibility of your website in search engine results.

In addition to improving SEO, using SSG can also help with indexing your pages and making them more easily discoverable by users.

## Using Solara's SSG feature.

### Requirements

Using SSR requires installation of [Playwright for Python](https://playwright.dev/python/). Follow their [installation instructions](https://playwright.dev/python/docs/library) or simply execute:


```
$ pip solara-enterprise[ssg]
$ playwright install
```

### Pre-deployment

Using the command

```
$ solara ssg your.awesome.app
```

Will run the solara server and use playwright to fetch all known pages and save them to the `../build` directory. Solara knows about your pages because of its [routing support](/docs/understanding/routing).

All HTML files in the `../build` will be used to pre-populate the HTML served to the user.

### During deployment

For fast and simpler deployment, you can also add the `--ssg` flag to the `solara run` command, e.g.:

```
$ solara run our.awesome.app --ssg
```

This will start you server immediately, and start a thread in the background that will fetch the known pages and put the in the `../build` directory, similar to the [pre-deployment](#pre-deployment) procedure.


The downsides of this method, is that users or crawlers may request a page when SSR is not done yet, leading to a slower page load or missing content for the crawler.

## Configuration

### Environment variables

 * `SOLARA_SSG_BUILD_PATH`: Override the directory where there html pages are stored.
 * `SOLARA_SSG_ENABLED`: Alternative to passing the `--ssg` flag. Should be used when running solara without `solara run` (e.g. using gunicorn/uvicorn).
 * `SOLARA_SSG_HEADED`: Run playwright using `headed` mode (in contrast to `headless`). Useful for debugging.

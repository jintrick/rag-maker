---
source_url: https://github.com/kagisearch/kagi-docs/blob/3fb47e284426fbd356307197717b5f167d3e868c/docs/orion/support-and-community/troubleshooting/troubleshooting-extension-issues.md
original_title: troubleshooting-extension-issues
fetched_at: 2026-06-21T02:50:48.213847+00:00
---

---
next:
  text: 'Troubleshooting Webpage Issues'
  link: '/orion/support-and-community/troubleshooting/troubleshooting-webpage-issues'
---

# Troubleshooting Extension Issues

Orion supports both Chrome and Firefox extensions natively. Note that this support is still experimental
and extensions may break or show unexpected behavior.

We recommend submitting such issues to
[orionfeedback.org](https://orionfeedback.org).

Here are some extra things you can do to help us debug this:



- Copy console errors from background-script [Tools->Extensions->Console (from options popup button for specific web-extension)]

<img src="../media/debug_ext.png" width="700" alt="Enable extension console"><br />

- Copy console errors from web-extension popup if applicable
- Copy console errors from current active tab (in case its related to tab communication or content script)
- Store URL for web-extension
- Specify exactly what things are not working
- Provide video or screenshot demonstrating extension working as expected with a chrome of firefox browser


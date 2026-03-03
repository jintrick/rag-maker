import subprocess
import json

catalog_path = "C:/Synology Drive/2way-sync/rag/electron/cache/catalog.json"
updates = [
    {"path": "docs/tutorial/devices.md", "title": "Device Access (Bluetooth, HID, USB, Serial)", "summary": "Guide to accessing hardware devices in Electron using Web Bluetooth, WebHID, Web Serial, and WebUSB APIs, including permission handling."},
    {"path": "docs/tutorial/devtools-extension.md", "title": "DevTools Extension", "summary": "How to load and use Chrome DevTools extensions in Electron for enhanced debugging capabilities."},
    {"path": "docs/tutorial/distribution-overview.md", "title": "Distribution Overview", "summary": "An overview of the different ways to package and distribute Electron applications for end-users."},
    {"path": "docs/tutorial/electron-timelines.md", "title": "Electron Timelines", "summary": "Understanding Electron's release cycle, supported versions, and the relationship with Chromium and Node.js versions."},
    {"path": "docs/tutorial/electron-versioning.md", "title": "Electron Versioning", "summary": "Detailed explanation of Electron's versioning scheme and how to manage upgrades."},
    {"path": "docs/tutorial/esm.md", "title": "ES Modules in Electron", "summary": "Guide to using ECMAScript Modules (ESM) in both the main and renderer processes of an Electron application."},
    {"path": "docs/tutorial/examples.md", "title": "Tutorial Examples", "summary": "A collection of practical examples and links to open-source Electron apps for learning."},
    {"path": "docs/tutorial/forge-overview.md", "title": "Electron Forge Overview", "summary": "Introduction to Electron Forge, the recommended tool for scaffolding, building, and publishing Electron apps."},
    {"path": "docs/tutorial/fuses.md", "title": "Electron Fuses", "summary": "Explains Electron Fuses, a mechanism to toggle packaged-time features without rebuilding Electron from source."},
    {"path": "docs/tutorial/in-app-purchases.md", "title": "In-App Purchases", "summary": "How to implement in-app purchases in Electron using the inAppPurchase API for macOS App Store builds."},
    {"path": "docs/tutorial/keyboard-shortcuts.md", "title": "Keyboard Shortcuts Guide", "summary": "Comprehensive guide on defining global and local keyboard shortcuts in Electron."},
    {"path": "docs/tutorial/launch-app-from-url-in-another-app.md", "title": "Launching App from URL", "summary": "How to register your Electron app as a default handler for a custom protocol URI."},
    {"path": "docs/tutorial/linux-desktop-actions.md", "title": "Linux Desktop Actions", "summary": "Guide to implementing Linux-specific desktop actions and shortcuts in the application menu."},
    {"path": "docs/tutorial/mac-app-store-submission-guide.md", "title": "Mac App Store Submission", "summary": "Step-by-step guide for signing and submitting Electron applications to the Mac App Store."},
    {"path": "docs/tutorial/macos-dock.md", "title": "macOS Dock Customization", "summary": "How to customize the application's dock icon, menu, and bounce effects on macOS."},
    {"path": "docs/tutorial/menus.md", "title": "Menus in Electron", "summary": "Comprehensive guide to creating and managing application and context menus using Menu and MenuItem."},
    {"path": "docs/tutorial/message-ports.md", "title": "Message Ports", "summary": "Using the MessagePort API for high-performance communication between different contexts in Electron."},
    {"path": "docs/tutorial/multithreading.md", "title": "Multithreading in Electron", "summary": "Techniques for offloading heavy tasks to background threads using Web Workers and Node.js worker threads."},
    {"path": "docs/tutorial/native-code-and-electron.md", "title": "Using Native Node Modules", "summary": "How to compile and use native C/C++ Node.js modules in your Electron application."},
    {"path": "docs/tutorial/native-file-drag-drop.md", "title": "Native File Drag and Drop", "summary": "Implementing native-like file drag-and-drop interactions from your app to the OS."},
    {"path": "docs/tutorial/navigation-history.md", "title": "Navigation History API", "summary": "Using the NavigationHistory API to manage and display browsing history in custom browser interfaces."},
    {"path": "docs/tutorial/notifications.md", "title": "Notifications Guide", "summary": "How to send and handle native OS notifications from both main and renderer processes."},
    {"path": "docs/tutorial/offscreen-rendering.md", "title": "Offscreen Rendering", "summary": "Using offscreen rendering to capture page content as bitmaps without displaying a window."},
    {"path": "docs/tutorial/online-offline-events.md", "title": "Online and Offline Events", "summary": "Monitoring and responding to the application's network connectivity status."},
    {"path": "docs/tutorial/performance.md", "title": "Performance Optimization", "summary": "Best practices and tips for optimizing the performance of Electron applications."},
    {"path": "docs/tutorial/progress-bar.md", "title": "Taskbar Progress Bar", "summary": "How to display and update an application's progress in the OS-native taskbar or dock."},
    {"path": "docs/tutorial/recent-documents.md", "title": "Recent Documents", "summary": "Managing and displaying a list of recently opened files in the OS-native application menu."},
    {"path": "docs/tutorial/repl.md", "title": "Electron REPL", "summary": "Using the Read-Eval-Print Loop (REPL) for interactive Electron development and debugging."},
    {"path": "docs/tutorial/represented-file.md", "title": "Represented File (macOS)", "summary": "Setting the represented file for a window to enable macOS-specific title bar features."},
    {"path": "docs/tutorial/snapcraft.md", "title": "Packaging for Snapcraft", "summary": "Guide to packaging and distributing Electron apps on Linux using the Snap format."},
    {"path": "docs/tutorial/spellchecker.md", "title": "Spellchecker Support", "summary": "Configuring and using Electron's built-in spellchecker for input fields."},
    {"path": "docs/tutorial/support.md", "title": "Support and Community", "summary": "Resources for getting help and staying connected with the Electron community."},
    {"path": "docs/tutorial/testing-on-headless-ci.md", "title": "Testing on Headless CI", "summary": "How to run automated Electron tests in headless environments like GitHub Actions."},
    {"path": "docs/tutorial/tray.md", "title": "System Tray Guide", "summary": "How to create and manage system tray icons, menus, and tooltips across different platforms."},
    {"path": "docs/tutorial/updates.md", "title": "Auto-Updater Guide", "summary": "Implementing automatic update mechanisms in Electron using the autoUpdater module or Electron Forge."},
    {"path": "docs/tutorial/using-native-node-modules.md", "title": "Native Modules Tutorial", "summary": "In-depth tutorial on compiling and managing native Node.js modules for Electron."},
    {"path": "docs/tutorial/using-pepper-flash-plugin.md", "title": "Pepper Flash (Deprecated)", "summary": "Note on the removal of Flash support in modern Electron versions."},
    {"path": "docs/tutorial/web-embeds.md", "title": "Embedding Web Content", "summary": "Comparison of iframe, webview, and WebContentsView for embedding third-party content."},
    {"path": "docs/tutorial/window-customization.md", "title": "Window Customization Overview", "summary": "Introduction to the various ways to customize BrowserWindow appearance and behavior."},
    {"path": "docs/tutorial/windows-arm.md", "title": "Windows on ARM Support", "summary": "Guide to building and testing Electron applications for Windows 10/11 on ARM devices."},
    {"path": "docs/tutorial/windows-store-guide.md", "title": "Windows Store Submission", "summary": "How to package and submit Electron apps to the Microsoft Store using the Desktop Bridge."},
    {"path": "docs/tutorial/windows-taskbar.md", "title": "Windows Taskbar Customization", "summary": "Detailed guide on customizing the application's presence in the Windows taskbar, including JumpLists and thumbnail toolbars."}
]

cmd = [
    "ragmaker-enrich-discovery",
    "--catalog-path", catalog_path,
    "--updates", json.dumps(updates)
]

print(f"Running command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

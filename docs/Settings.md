# Settings

The settings modal can be accessed by clicking the gear icon in the top-right corner of the display. It contains tabs for Display, Images, Library, and About.

## Library

The Library tab provides cache configuration and maintenance tasks for managing the photo library.

![Library Settings](images/settings/librarySettings.png)

### Cache

| Setting | Description | Range |
|---------|-------------|-------|
| Cache Timeout | How long (in seconds) a processed image stays in the cache before being evicted. | 0 – 604800 |

### Maintenance

These actions run asynchronously in the background. A progress toast appears in the bottom-right corner while a task is running.

| Action | Description |
|--------|-------------|
| Reset Image Count | Resets the view count for all images back to zero. This causes the display rotation to start fresh. |
| Clear Cache | Clears all cached processed images. Images will be re-processed on next display. |
| Rescan Library | Re-scans the configured library directories for new, removed, or restored images. |

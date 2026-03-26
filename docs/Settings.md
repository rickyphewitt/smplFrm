# Settings

The settings modal can be accessed by clicking the SmplFrm icon in the top-right corner of the display. It contains tabs for Display, Images, Library, Presets, Tasks, and About.

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

## Presets

The Presets tab displays all configuration presets and custom configs. It allows switching between configs and managing custom ones. Configs are sorted with the active config first, then system-managed presets, then custom configs. Paginated with 5 per page.

![Presets Settings](images/settings/presetSettings.png)

| Column      | Description                                                                                      |
|-------------|--------------------------------------------------------------------------------------------------|
| Name        | The config name. Editable inline for custom configs.                                             |
| Description | A brief description. Editable inline for custom configs.                                         |
| Status      | Shows "Active" badge for the current config, or an "Activate" button to switch to that config.   |
| Delete      | Delete button (×) for inactive custom configs. Lock icon (🔒) for system-managed or active configs. |

### Behavior

- **Activating a config** reloads the page with the new config applied.
- **Editing settings** (Display, Images, Library tabs) while a system-managed config is active automatically creates a custom copy. The original preset is never modified.
- **System-managed presets** (prefixed with `smplFrm`) cannot be edited or deleted. They are synced from JSON files on app startup.
- **Custom configs** can be renamed, have their description edited, and be deleted (if not active).
- A maximum of 10 configs can exist at a time.

## Tasks

The Tasks tab displays a history of background tasks. Each row shows the task type, status, progress, and creation date. Tasks are sorted newest-first and paginated with 5 per page.

![Task Settings](images/settings/taskSettings.png)

| Column   | Description                                            |
|----------|--------------------------------------------------------|
| Type     | The task name (e.g. Clear Cache, Rescan Library).      |
| Status   | Current state: pending, running, completed, or failed. |
| Progress | Completion percentage (0–100%).                        |
| Created  | Date and time the task was created.                    |
| Delete   | Delete a task.                                         |

Each row includes a delete button (×) that deletes the task. If the task is currently running, it will self-cancel on its next progress check.

Only one task of each type can be pending or running at a time. Attempting to start a duplicate will show an error in the toast.

Tasks that were created more than 7 days ago will be deleted. 
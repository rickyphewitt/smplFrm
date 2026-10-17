class Theme:
    """A named stylesheet selectable per config.

    Attributes:
        id: Stable string identifier. Also the JSON:API resource id for this
            theme in the themes collection, so there is one identifier with
            one name and no mapping layer.
        label: Shown in the UI (Display tab dropdown, themes endpoint).
        description: One line, shown in the UI as helper text.
        stylesheet: A path resolvable by Django's `static` machinery, not a
            bare filename and not a URL. Never serialized to a client.
        preload_fonts: Static paths of `woff2` faces the page needs before
            first paint, emitted as `<link rel="preload">` ahead of the
            stylesheets. Keep this to the faces used above the fold; every
            entry is fetched on every page load whether or not it is used.
            Never serialized to a client.
    """

    def __init__(
        self,
        id: str,
        label: str,
        description: str,
        stylesheet: str,
        preload_fonts: tuple[str, ...] = (),
    ):
        self.id = id
        self.label = label
        self.description = description
        self.stylesheet = stylesheet
        self.preload_fonts = tuple(preload_fonts)

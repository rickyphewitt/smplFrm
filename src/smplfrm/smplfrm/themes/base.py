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
    """

    def __init__(self, id: str, label: str, description: str, stylesheet: str):
        self.id = id
        self.label = label
        self.description = description
        self.stylesheet = stylesheet

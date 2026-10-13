from smplfrm.themes.base import Theme


class ClassicTheme(Theme):
    """The original smplFrm look, extracted into its own stylesheet."""

    def __init__(self):
        super().__init__(
            id="classic",
            label="Classic",
            description="The original smplFrm look",
            stylesheet="css/theme-classic.css",
        )

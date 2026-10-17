from smplfrm.themes.base import Theme


class ClassicTheme(Theme):
    """The Classic smplFrm look, styled by static/css/theme-classic.css."""

    def __init__(self):
        super().__init__(
            id="classic",
            label="Classic",
            description="The original smplFrm look",
            stylesheet="css/theme-classic.css",
        )

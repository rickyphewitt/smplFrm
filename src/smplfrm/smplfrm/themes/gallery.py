from smplfrm.themes.base import Theme


class GalleryTheme(Theme):
    """A museum wall label beside the photo, styled by static/css/theme-gallery.css.

    Preloads the two faces drawn on the frame before first paint: EB Garamond
    for the photo date and Geist for the meta line beneath it.
    """

    def __init__(self):
        super().__init__(
            id="gallery",
            label="Gallery (beta)",
            description="A quiet wall label beside the photo",
            stylesheet="css/theme-gallery.css",
            preload_fonts=(
                "fonts/eb-garamond/eb-garamond-latin-400-normal.woff2",
                "fonts/geist/geist-latin-400-normal.woff2",
            ),
        )

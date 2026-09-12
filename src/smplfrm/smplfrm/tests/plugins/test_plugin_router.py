from django.test import TestCase


class TestPluginRouter(TestCase):

    def test_plugin_router_includes_spotify_routes(self):
        from smplfrm.plugins import get_plugin_router

        router = get_plugin_router()
        urls = [
            (
                url.pattern.regex.pattern
                if hasattr(url.pattern, "regex")
                else str(url.pattern)
            )
            for url in router.urls
        ]
        url_str = " ".join(urls)
        self.assertIn("spotify", url_str)

    def test_plugin_router_includes_weather_routes(self):
        from smplfrm.plugins import get_plugin_router

        router = get_plugin_router()
        urls = [
            (
                url.pattern.regex.pattern
                if hasattr(url.pattern, "regex")
                else str(url.pattern)
            )
            for url in router.urls
        ]
        url_str = " ".join(urls)
        self.assertIn("weather", url_str)

    def test_spotify_endpoints_accessible(self):
        """Verify spotify plugin endpoints are reachable via auto-discovered router."""
        response = self.client.get("/api/v1/plugins/spotify/status")
        # 401 = not authorized, 412 = not configured - both mean endpoint exists
        self.assertIn(response.status_code, [200, 401, 412])

    def test_weather_endpoint_accessible(self):
        """Verify weather plugin endpoint is reachable via auto-discovered router."""
        response = self.client.get("/api/v1/plugins/weather/current")
        self.assertEqual(response.status_code, 200)

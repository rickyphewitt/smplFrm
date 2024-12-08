from http.server import HTTPServer, SimpleHTTPRequestHandler
from http import HTTPStatus
from tempfile import template
import urllib.parse

from services.image_service import ImageService
from services.template_service import TemplateService
import settings
import os

PORT = 8000

class ImageServer(SimpleHTTPRequestHandler):

    def __init__(self, *args, directory=None, **kwargs):
        # @ToDo handle loading images better
        # instead of on each request, the server
        # should load them once
        self.image_service = ImageService()
        self.template_service = TemplateService()
        super().__init__(*args, directory=directory, **kwargs)


    def do_GET(self):

        # decode path
        path = urllib.parse.unquote(self.path)
        self.send_response(HTTPStatus.OK)
        if "favicon" in path:
            # ToDo add a favicon.ico package
            self.send_response(HTTPStatus.NOT_FOUND)
        elif "/next" in path:
            #@TODO not needed after a real framework (DJANGO)
            self.image_service.load_images()
            # run get next image logic
            width = self.headers.get("window-w", 100)
            height = self.headers.get("window-h", 100)
            # manipulate image to screensize
            scaled_image = None
            next_image = self.image_service.get_next()
            try:
                scaled_image = self.image_service.display_image(next_image["path"], window_height=height, window_width=width)
            except Exception:
                self.send_response(HTTPStatus.NOT_FOUND)
                self.send_header('Content-type', 'image/jpeg')
                self.end_headers()

            # else all is good and return image
            self.send_response(HTTPStatus.OK)

            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(scaled_image)
        else:
            # run normal server startup logic
            self.image_service.load_images()
            image = self.image_service.get_one()
            template = self.template_service.render("image.html", image=image["name"])
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(template, "utf8"))



httpd = HTTPServer(('0.0.0.0', PORT), ImageServer)
httpd.serve_forever()
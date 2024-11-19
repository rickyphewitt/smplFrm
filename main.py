from http.server import HTTPServer, SimpleHTTPRequestHandler
from http import HTTPStatus
from tempfile import template

from services.image_service import ImageService
from services.template_service import TemplateService
import settings
import os

PORT = 8000

class ImageServer(SimpleHTTPRequestHandler):

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
        self.image_service = ImageService()

    def do_GET(self):
        self.image_service = ImageService()
        self.template_service = TemplateService()
        self.image_service.load_images()
        image = self.image_service.get_one()

        if "favicon" in self.path:
            self.send_response(HTTPStatus.NOT_FOUND)
            return

        # handle the image being returned
        if len(self.path) > 10 and "favicon" not in self.path:
            self.send_response(HTTPStatus.OK)
            width = self.headers.get("window-w", 0)
            height = self.headers.get("window-h", 0)

            if int(width) > 0 and int(height) > 0:
                # manipulate image to screensize
                scaled_image = self.image_service.scale(image[1], window_height=height, window_width=width)

            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(scaled_image)
            # with open(self.path, "rb") as f:
            #     self.wfile.write(f.read())

        # default loading of template
        self.image_service.load_images()
        image = self.image_service.get_one()
        template = self.template_service.render("image.html", image=image[1])
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(template, "utf8"))

httpd = HTTPServer(('0.0.0.0', PORT), ImageServer)
httpd.serve_forever()
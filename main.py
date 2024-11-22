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
        # @ToDo handle loading images better
        # instead of on each request, the server
        # should load them once
        self.image_service = ImageService()
        self.template_service = TemplateService()
        self.image_service.load_images()
        super().__init__(*args, directory=directory, **kwargs)


    def do_GET(self):

        if "favicon" in self.path:
            self.send_response(HTTPStatus.NOT_FOUND)
            return

        # handle the image being returned
        if len(self.path) > 3: # greater than 3 means a file extension ".jpg, .png, ect"
            width = self.headers.get("window-w", 0)
            height = self.headers.get("window-h", 0)

            if int(width) > 0 and int(height) > 0:
                # manipulate image to screensize
                try:
                    scaled_image = self.image_service.scale(self.path, window_height=height, window_width=width)
                except Exception:
                    self.send_response(HTTPStatus.NOT_FOUND)
                    self.send_header('Content-type', 'image/jpeg')
                    self.end_headers()
                    return
            # else all is good and return image
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(scaled_image)

        # default loading of template
        image = self.image_service.get_one()
        template = self.template_service.render("image.html", image=image[1])
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(template, "utf8"))

httpd = HTTPServer(('0.0.0.0', PORT), ImageServer)
httpd.serve_forever()
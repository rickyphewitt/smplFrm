from http.server import HTTPServer, SimpleHTTPRequestHandler
from http import HTTPStatus
from services.image_service import ImageService
import settings
import os

PORT = 8000

class ImageServer(SimpleHTTPRequestHandler):

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
        self.image_service = ImageService()

    def do_GET(self):

        # handle the image being returned
        if len(self.path) > 10:
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            with open(self.path, "rb") as f:
                self.wfile.write(f.read())

        # default loading of template
        self.image_service = ImageService()
        self.image_service.load_images()
        image = self.image_service.get_one()
        template_raw = ""
        with open(settings.IMAGE_TEMPLATE, 'r') as f:
            template_raw = f.read()

        template = template_raw.replace("{{image}}", image[1])

        self.send_response(HTTPStatus.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes(template, "utf8"))

httpd = HTTPServer(('localhost', PORT), ImageServer)
httpd.serve_forever()
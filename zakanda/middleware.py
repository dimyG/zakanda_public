class PjaxMiddleware():
    # we add the X-PJAX-URL header to all responses. This is needed when a form is submitted with pjax
    # and it redirects to another url afterwards. Pjax does the redirection but it doesn't update the
    # url in the browser. To be able to do so, it needs to read the url from this header.
    def process_response(self, request, response):
        response['X-PJAX-URL'] = request.build_absolute_uri()
        return response

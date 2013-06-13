#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################

'''
Simple HTTP server for the Flight Data Parameter Designer.
'''

################################################################################
# Imports (#1)


import argparse
import logging
import os
import simplejson
import socket
import sys
import webbrowser

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from cgi import FieldStorage
from datetime import date
from jinja2 import Environment, PackageLoader
from tempfile import mkstemp
from urlparse import urlparse, parse_qs

from analysis_engine.library import align


################################################################################
# Logging Configuration


logging.getLogger('analysis_engine').addHandler(logging.NullHandler())


################################################################################
# Imports (#2)


from hdfaccess.file import hdf_file

from browser import register_additional_browsers


################################################################################
# Constants


DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8080

ENVIRONMENT = 'test'
SUFFIX = '' if ENVIRONMENT == 'production' else '-%s' % ENVIRONMENT
BASE_URL = 'https://polaris%s.flightdataservices.com' % SUFFIX

FILE_EXT_MODE_MAP = {
    # Images:
    'gif': 'rb',
    'ico': 'rb',
    'jpg': 'rb',
    'png': 'rb',
}
FILE_EXT_TYPE_MAP = {
    # Styles:
    'css': 'text/css',
    # Scripts:
    'js': 'text/javascript',
    'json': 'application/json',
    # Images:
    'gif': 'image/gif',
    'ico': 'image/x-icon',
    'jpg': 'image/jpeg',
    'png': 'image/png',
}

APPDATA_DIR = '_assets/'
if getattr(sys, 'frozen', False):
    APPDATA_DIR = os.path.join(os.environ.get('APPDATA', '.'), 'FlightDataServices', 'FlightDataParameterDesigner')
    if not os.path.isdir(APPDATA_DIR):
        print "Making Application data directory: %s" % APPDATA_DIR
        os.makedirs(APPDATA_DIR)
        

AJAX_DIR = os.path.join(APPDATA_DIR, 'ajax')
if not os.path.isdir(AJAX_DIR):
    print "Making AJAX directory: %s" % AJAX_DIR
    os.makedirs(AJAX_DIR)
    
socket.setdefaulttimeout(120)
    
################################################################################
# Helpers


def parse_arguments():
    '''
    '''

    def port_range(string):
        '''
        Range type used by argument parser for port values.
        '''
        try:
            value = int(string)
            if not 0 < value <= 65535:
                raise ValueError('Port number out-of-range.')
        except:
            msg = '%r is not a valid port number' % string
            raise argparse.ArgumentTypeError(msg)
        return value

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Flight Data Parameter Tree Viewer',
    )

    parser.add_argument('-n', '--no-browser',
        action='store_false',
        dest='browser',
        help='Don\'t launch a browser when starting the server.',
    )

    parser.add_argument('-p', '--port',
        default=DEFAULT_PORT,
        type=port_range,
        help='Port on which to run the server (default: %(default)d)',
    )

    return parser.parse_args()


def lookup_path(relative_path):
    '''
    Convert a relative path to the asset path. Accounts for being frozen.
    '''
    file_path = relative_path.lstrip('/').replace('/', os.sep)
    if getattr(sys, 'frozen', False):
        # http://www.pyinstaller.org/export/v1.5.1/project/doc/Manual.html?format=raw#accessing-data-files
        if '_MEIPASS2' in os.environ:
            # --onefile distribution
            return os.path.join(os.environ['_MEIPASS2'], file_path)
        else:
            # --onedir distribution
            return os.path.join(os.path.dirname(sys.executable), file_path)
    else:
        return file_path


################################################################################
# Handlers


class DesignRequestHandler(BaseHTTPRequestHandler):
    '''
    '''

    _template_pkg = ('flightdataparameterdesigner', lookup_path('templates'))
    _template_env = Environment(loader=PackageLoader(*_template_pkg))

    ####################################
    # Response Helper Methods

    def _respond(self, body, status=200, content_type='text/html'):
        '''
        Respond with body setting status and content-type.
        '''
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(body)

    def _respond_with_template(self, template_path, context={}, **kwargs):
        '''
        Respond with a rendered template.
        '''
        template = self._template_env.get_template(template_path)
        self._respond(template.render(**context).encode('utf-8'), **kwargs)
    
    def _respond_with_json(self, data, **kwargs):
        self._respond(simplejson.dumps(data), **kwargs)

    def _respond_with_error(self, status, message):
        '''
        Respond with error status code and message.
        '''
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.send_error(status, message)

    def _respond_with_static(self, path):
        '''
        '''
        # Lookup the file and content type:
        file_path = lookup_path(path)
        ext = os.path.splitext(file_path)[-1][1:]  # Remove the leading dot.
        mode_ = FILE_EXT_MODE_MAP.get(ext, 'r')
        type_ = FILE_EXT_TYPE_MAP.get(ext, 'text/html')

        # Attempt to serve resource from the current directory:
        self._respond(open(file_path, mode_).read(), 200, type_)

    ####################################
    # HTTP Method Handlers

    def do_POST(self):
        '''
        '''
        if self.path.endswith('/design'):
            self._design()
            return
        elif self.path.endswith('/generate_graph'):
            self._generate_graph()
            return
        elif self.path.endswith('/code_run'):
            self._code_run()
            return        
        self._respond_with_error(404, 'Page Not Found %s' % self.path)

    def do_GET(self):
        '''
        '''
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path == '/':
            self._index()  # File upload page with aircraft information.
            return
        elif path.endswith('/design'):
            self._index()  # Redirect to index if no HDF file in POST.
            return
        elif path.startswith('/_assets'):
            try:
                self._respond_with_static(path)
                return
            except IOError:
                pass
        self._respond_with_error(404, 'Page Not Found %s' % self.path)

    ####################################
    # Page Response Methods

    def _index(self, error=None):
        '''
        :param error: Optional error to display with the form.
        :type error: str
        '''
        self._respond_with_template('index.html', {
            'error': error,
            'year': date.today().year,
        })

    def _design(self):
        '''
        '''
        form = FieldStorage(
            self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'},
        )

        # Handle uploading of an HDF file:
        file_upload = form['hdf_file']
        if not file_upload.filename:
            self._index(error='Please select a file to upload.')
            return
        # Create a temporary file for the upload:
        file_desc, file_path = mkstemp()
        file_obj = os.fdopen(file_desc, 'w')
        file_obj.write(file_upload.file.read())
        file_obj.close()
        try:
            with hdf_file(file_path) as hdf_file_obj:
                parameter_names = hdf_file_obj.keys()
        except IOError:
            self._index(error='Please select a valid HDF file.')
            return

        self._respond_with_template('design.html', {
            'parameter_names': parameter_names,
            'file_path': file_path,
        })
    
    
    def _parse_post(self):
        length = int(self.headers['content-length'])
        return parse_qs(self.rfile.read(length), 
                            keep_blank_values=1)        
    
    def _generate_graph(self):
        postvars = self._parse_post()
        data = []
        with hdf_file(postvars['file_path'][0]) as hdf:
            params = hdf.get_params(postvars['parameters[]']).values()
        
        align_param = params[0]
        arrays = [align_param[0]]
        
        for param in align_param:
            arrays.append(align(param, align_param))
        
        # TODO: Get parameter data and return it as AJAX.
        for param in params.values():
            data.append(zip(range(len(param.array)), param.array.data.tolist()))
        return self._respond_with_json({'data': data})
    
    
    def _prepare_array(self, array):
        return [zip(range(len(array)), array.data.tolist())]
    
    
    def _code_run(self):
        postvars = self._parse_post()
        import numpy as np
        from analysis_engine.node import A, KTI, KPV, S, P
        from analysis_engine.library import *
        
        data = []
        try:
            with hdf_file(postvars['file_path'][0]) as hdf:
                if postvars['var_name_1'][0]:
                    exec "%s = hdf['%s']" % (postvars['var_name_1'][0], postvars['hdf_name_1'][0])
                    data.append(self._prepare_array(locals()[postvars['var_name_1'][0]].array))
                if postvars['var_name_2'][0]:
                    exec "%s = hdf['%s']" % (postvars['var_name_2'][0], postvars['hdf_name_2'][0])
                    data.append(self._prepare_array(locals()[postvars['var_name_2'][0]].array))
                if postvars['var_name_3'][0]:
                    exec "%s = hdf['%s']" % (postvars['var_name_3'][0], postvars['hdf_name_3'][0])
                    data.append(self._prepare_array(locals()[postvars['var_name_3'][0]].array))
            
                exec postvars['code'][0]
            data.insert(0, self._prepare_array(result))
        except Exception as err:
            return self._respond_with_json({'error': str(err)})
        # TODO: Align.
        # TODO: Remove invalid/masked dependencies
        # TODO: Use ast module to parse code.
        return self._respond_with_json({'data': data})


################################################################################
# Program


if __name__ == '__main__':
    print 'FlightDataParameterDesigner (c) Copyright 2013 Flight Data Services, Ltd.'
    print '  - Powered by POLARIS'
    print '  - http://www.flightdatacommunity.com'
    print ''
    opt = parse_arguments()

    url = 'http://%s:%d/' % (DEFAULT_HOST, opt.port)

    server = HTTPServer((DEFAULT_HOST, opt.port), DesignRequestHandler)
    print >>sys.stderr, 'Spacetree server is running at %s' % url
    print >>sys.stderr, 'Quit the server with CONTROL-C.'

    if opt.browser:
        print >>sys.stderr, 'Registering additional web browsers...'
        register_additional_browsers()
        print >>sys.stderr, 'Launching viewer in a web browser...'
        webbrowser.open_new_tab(url)
    else:
        print >>sys.stderr, 'Browse to the above location to use the viewer...'

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print >>sys.stderr, '\nShutting down server...'
        server.socket.close()


################################################################################
# vim:et:ft=python:nowrap:sts=4:sw=4:ts=4

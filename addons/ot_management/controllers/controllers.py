# -*- coding: utf-8 -*-
from odoo import http

# class OtManagement(http.Controller):
#     @http.route('/ot_management/ot_management/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ot_management/ot_management/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ot_management.listing', {
#             'root': '/ot_management/ot_management',
#             'objects': http.request.env['ot_management.ot_management'].search([]),
#         })

#     @http.route('/ot_management/ot_management/objects/<model("ot_management.ot_management"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ot_management.object', {
#             'object': obj
#         })